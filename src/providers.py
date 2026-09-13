"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có dữ liệu lịch khám thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.casefold()
        has_observation = "mcp observation" in prompt_lower
        asks_for_booking = "đặt" in prompt_lower or "dat " in prompt_lower or "đăng ký" in prompt_lower
        asks_multi_step = asks_for_booking and any(
            marker in prompt_lower
            for marker in ("sau đó", "sau khi", "rồi", "nếu có", "tra cứu lịch", "tìm lịch", "tìm bác sĩ")
        )

        def extract_specialty() -> str:
            specialties = {
                "tim mạch": "Tim mạch",
                "tim mach": "Tim mạch",
                "da liễu": "Da liễu",
                "da lieu": "Da liễu",
                "nhi khoa": "Nhi khoa",
            }
            for keyword, display_name in specialties.items():
                if keyword in prompt_lower:
                    return display_name
            specialty_match = re.search(
                r"chuyên khoa\s+(.+?)(?=\s+tại|\s+ngày|\s+ưu tiên|[,\n.]|$)",
                prompt,
                re.IGNORECASE,
            )
            if specialty_match:
                return specialty_match.group(1).strip()
            return "Tim mạch"

        def extract_date() -> str:
            match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", prompt)
            return match.group(1) if match else "20/09/2026"

        def extract_datetime() -> str:
            match = re.search(
                r"(\d{1,2}:\d{2})\s*(?:ngày\s*)?(\d{1,2}/\d{1,2}/\d{4})",
                prompt,
                re.IGNORECASE,
            )
            if match:
                return f"{match.group(1)} {match.group(2)}"
            slot_match = re.search(r'"available_slots"\s*:\s*\[\s*"([^"]+)"', prompt)
            return slot_match.group(1) if slot_match else f"08:30 {extract_date()}"

        def extract_doctor() -> str:
            observation_match = re.search(r'"doctor_name"\s*:\s*"([^"]+)"', prompt)
            if observation_match:
                return observation_match.group(1)
            explicit_match = re.search(
                r"bác sĩ\s+(.+?)(?=\s+vào lúc|\s+ngày|\s+tại|[,\n]|$)",
                prompt,
                re.IGNORECASE,
            )
            if explicit_match:
                return explicit_match.group(1).strip()
            defaults = {
                "Tim mạch": "PGS.TS Nguyễn Hoàng Nam",
                "Da liễu": "BS.CKII Trần Minh Anh",
                "Nhi khoa": "TS.BS Lê Thu Hà",
            }
            return defaults[extract_specialty()]

        def extract_patient_name() -> str:
            match = re.search(
                r"(?:bệnh nhân|cho bệnh nhân|tên là)\s+(.+?)(?=\s+(?:với|vào|ngày|tại|vì)|[,\n]|$)",
                prompt,
                re.IGNORECASE,
            )
            return match.group(1).strip() if match else "Nguyễn An"

        def extract_location() -> str:
            if "vinmec central park" in prompt_lower:
                return "Vinmec Central Park"
            return "Vinmec Times City"

        def extract_reason() -> str:
            match = re.search(r"(?:vì|lý do khám là)\s+(.+?)(?:[.\n]|$)", prompt, re.IGNORECASE)
            return match.group(1).strip() if match else "Khám theo nhu cầu của bệnh nhân"

        def extract_time_preference() -> str:
            if "buổi sáng" in prompt_lower or "sáng" in prompt_lower:
                return "buổi sáng"
            if "buổi chiều" in prompt_lower or "chiều" in prompt_lower:
                return "buổi chiều"
            return "bất kỳ"

        # Sau mỗi Observation, Mock tiếp tục vòng ReAct hoặc trả lời cuối cùng.
        if has_observation:
            if asks_for_booking and "booking_id" not in prompt_lower and '"available_slots"' in prompt_lower:
                return {
                    "type": "tool_call",
                    "tool_name": "book_medical_appointment",
                    "arguments": {
                        "patient_name": extract_patient_name(),
                        "specialty": extract_specialty(),
                        "doctor_name": extract_doctor(),
                        "appointment_datetime": extract_datetime(),
                        "location": extract_location(),
                        "reason": extract_reason(),
                    },
                    "thought": "Đã nhận được bác sĩ và khung giờ hợp lệ từ Observation. Tôi sẽ dùng dữ liệu đó để đặt lịch khám.",
                }

            if "not_found" in prompt_lower:
                content = "Chưa tìm thấy lịch khám cho chuyên khoa này. Bạn có thể thử một chuyên khoa khác."
            elif "no_availability" in prompt_lower:
                content = "Hiện chưa có khung giờ phù hợp với điều kiện bạn chọn. Mình chưa tạo lịch khám."
            elif "booking_id" in prompt_lower:
                content = "Đã đặt lịch khám Vinmec thành công theo bác sĩ và khung giờ đã xác nhận."
            else:
                content = "Đã tìm thấy lịch bác sĩ phù hợp. Bạn có thể chọn một khung giờ để tiếp tục đặt lịch."
            return {
                "type": "text",
                "content": content,
                "thought": "Đã nhận được Observation từ MCP Server và đủ dữ liệu để trả lời người dùng.",
            }

        # Với yêu cầu nhiều bước, luôn tra cứu trước để lấy bác sĩ và khung giờ.
        if asks_multi_step:
            return {
                "type": "tool_call",
                "tool_name": "doctor_schedule_query",
                "arguments": {
                    "specialty": extract_specialty(),
                    "preferred_date": extract_date(),
                    "location": extract_location(),
                    "time_preference": extract_time_preference(),
                },
                "thought": "Tôi cần tra cứu lịch bác sĩ trước để chỉ đặt một khung giờ đang còn trống.",
            }

        # Mô phỏng nhận diện intent gọi Tool cho các yêu cầu một bước.
        if asks_for_booking:
            return {
                "type": "tool_call",
                "tool_name": "book_medical_appointment",
                "arguments": {
                    "patient_name": extract_patient_name(),
                    "specialty": extract_specialty(),
                    "doctor_name": extract_doctor(),
                    "appointment_datetime": extract_datetime(),
                    "location": extract_location(),
                    "reason": extract_reason(),
                },
                "thought": "Người dùng đã cung cấp bác sĩ và khung giờ. Tôi sẽ gọi tool book_medical_appointment.",
            }
        elif any(keyword in prompt_lower for keyword in ("lịch", "bác sĩ", "chuyên khoa", "khám", "tra cứu")):
            return {
                "type": "tool_call",
                "tool_name": "doctor_schedule_query",
                "arguments": {
                    "specialty": extract_specialty(),
                    "preferred_date": extract_date(),
                    "location": extract_location(),
                    "time_preference": extract_time_preference(),
                },
                "thought": "Người dùng cần dữ liệu lịch khám thực tế. Tôi sẽ tra cứu bác sĩ và khung giờ phù hợp.",
            }
        else:
            return {
                "type": "text",
                "content": "Mình có thể hỗ trợ tra cứu lịch bác sĩ và đặt lịch khám tại Vinmec. Mình không chẩn đoán hoặc tư vấn điều trị.",
                "thought": "Đây là câu hỏi chung về phạm vi dịch vụ, chưa cần gọi Tool.",
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()

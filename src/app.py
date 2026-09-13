"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import re
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPVinmecServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def clean_final_answer(content: str) -> str:
    """Làm sạch Markdown thô để câu trả lời hiển thị tự nhiên trong giao diện chat."""
    cleaned = (content or "")
    cleaned = re.sub(r"(?m)^\s*\*\s+", "- ", cleaned)
    return cleaned.replace("*", "")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def _build_react_prompt(user_query: str, observations: list) -> str:
    """Tạo prompt cho lượt kế tiếp, giữ lại các Observation của MCP Server."""
    if not observations:
        return user_query

    observation_lines = []
    for item in observations:
        observation_lines.append(
            f"- Tool {item['tool_name']}({json.dumps(item['arguments'], ensure_ascii=False)}) "
            f"trả về: {json.dumps(item['observation'], ensure_ascii=False)}"
        )

    return (
        f"Yêu cầu ban đầu của người dùng:\n{user_query}\n\n"
        "MCP OBSERVATION từ các bước trước:\n"
        + "\n".join(observation_lines)
        + "\n\nTiếp tục vòng ReAct. Nếu còn hành động cần thiết, hãy gọi Tool phù hợp; "
          "nếu đã đủ dữ liệu, hãy trả lời cuối cùng bằng văn bản."
    )


def run_react_agent(user_query: str, provider, mcp_server: MCPVinmecServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    observations = []
    tools_list = mcp_server.list_tools()

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gửi yêu cầu ban đầu hoặc yêu cầu đã bổ sung Observation cho LLM.
        step_prompt = _build_react_prompt(user_query, observations)
        llm_response = provider.generate_with_tools(
            step_prompt,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        ) or {}
        latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp.
        if llm_response.get("type") == "text":
            final_content = clean_final_answer(
                llm_response.get("content", "") or "Agent không tạo ra nội dung trả lời."
            )
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms,
            })
            break

        # Trường hợp 2: LLM đề xuất gọi Tool (Action).
        if llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {}) or {}
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            # Thực thi Tool qua MCP Server và lấy Observation có cấu trúc.
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {}) or {}
            obs_str = json.dumps(obs_data, ensure_ascii=False)
            print(f"👁️ [Observation từ MCP Server]: {obs_str}")

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "thought": thought,
                "latency_ms": latency_ms,
            })
            observations.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
            })
            print("🔁 [ReAct]: Đã nạp Observation, chuyển sang lượt suy luận tiếp theo.")
            continue

        # Provider trả về cấu trúc không hợp lệ.
        final_content = "Agent trả về phản hồi không hợp lệ."
        print(f"⚠️ [Agent Error]: {final_content}")
        trace_logs.append({
            "step": step,
            "query": user_query,
            "action_type": "FINAL_ANSWER",
            "thought": "Phản hồi từ provider không có type hợp lệ.",
            "output": final_content,
            "latency_ms": latency_ms,
        })
        break

    if step >= MAX_ITERATIONS and (not trace_logs or trace_logs[-1].get("action_type") != "FINAL_ANSWER"):
        final_content = "Agent đã đạt giới hạn số vòng suy luận trước khi hoàn tất yêu cầu."
        print(f"🏁 [Final Answer]: {final_content}")
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "FINAL_ANSWER",
            "thought": "Đã đạt giới hạn MAX_ITERATIONS.",
            "output": final_content,
            "latency_ms": 0.0,
        })

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏥 VINMEC CARE COORDINATOR - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPVinmecServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Phạm vi trợ lý: 'Vinmec có thể hỗ trợ những việc gì?'")
        print("   - Tra cứu lịch: 'Hãy tra cứu lịch khám Da liễu ngày 21/09/2026'")
        print("   - Đặt lịch khám: 'Hãy đặt lịch Da liễu với bác sĩ Trần Minh Anh'")
        print("   - Luồng đa bước: 'Tìm lịch Tim mạch rồi đặt khung giờ buổi sáng'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu lịch khám) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")

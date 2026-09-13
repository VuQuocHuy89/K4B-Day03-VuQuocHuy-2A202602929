"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPVinmecServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol.
    """
    def __init__(self, server_name: str = "vinmec-care-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        raw_result = dispatch_tool_call(tool_name, arguments)
        try:
            content = json.loads(raw_result)
        except (TypeError, json.JSONDecodeError) as exc:
            content = {
                "status": "EXECUTION_ERROR",
                "error": f"Tool trả về JSON không hợp lệ: {exc}"
            }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinmec-care-mcp-server)")
    print("==========================================================")
    
    server = MCPVinmecServer(server_name="vinmec-care-mcp-server")
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra trạng thái Tool Schema
    booking_tool = next((t for t in tools if t.get("name") == "book_medical_appointment"), None)
    if booking_tool and not booking_tool.get("parameters", {}).get("properties"):
        print("⏳ [SCHEMA]: Tool 'book_medical_appointment' chưa được định nghĩa properties trong 'src/tools.py'.")
    else:
        print("✅ [SCHEMA]: Tool 'book_medical_appointment' đã có schema đầy đủ.")

    # Kiểm tra call_tool
    test_result = server.call_tool(
        "doctor_schedule_query",
        {
            "specialty": "Tim mạch",
            "preferred_date": "20/09/2026",
            "location": "Vinmec Times City",
            "time_preference": "buổi sáng",
        },
    )
    if not test_result:
        print("⏳ [MCP]: Hàm call_tool() đang trả về rỗng.")
    else:
        print("✅ [MCP]: Test dispatch tool 'doctor_schedule_query' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")

# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Vũ Quốc Huy  
> **Mã Sinh Viên / Mã Học viên:** 2A202602929  
> **Chủ đề Lựa chọn:** Vinmec Care Coordinator — Trợ lý điều phối lịch khám chuyên khoa  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | **5 / 5** | Agent phân tích chuyên khoa, ngày, cơ sở và khung giờ; với yêu cầu đặt lịch, Agent tra cứu trước rồi mới đặt. |
| **2. Tool Interaction** | **5 / 5** | Agent sử dụng Tool tra cứu lịch và Tool đặt lịch thông qua MCP Server. |
| **3. Dynamic Decision** | **5 / 5** | Hành động đặt lịch phụ thuộc vào kết quả lịch còn trống từ bước tra cứu. |
| **4. Long Horizon Goal** | **4 / 5** | Mục tiêu có thể gồm nhiều hành động liên tiếp, trong phạm vi hai Tool của bài lab. |
| **TỔNG ĐIỂM AGENTIC FIT** | **19 / 20** | Bài toán phù hợp cao với Agentic System. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Trace bên dưới được sinh từ lần chạy với **Gemini API thật** bằng lệnh `python src/app.py --all`.

Dán một đoạn trace tiêu biểu của TC04:

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "doctor_schedule_query",
    "arguments": {
      "specialty": "Tim mạch",
      "preferred_date": "20/09/2026",
      "location": "Vinmec Times City",
      "time_preference": "buổi sáng"
    },
    "observation": {
      "status": "SUCCESS",
      "doctors": [
        {
          "doctor_name": "PGS.TS Nguyễn Hoàng Nam",
          "available_slots": ["08:30 20/09/2026", "10:30 20/09/2026"]
        }
      ]
    },
    "latency_ms": 446.34
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "book_medical_appointment",
    "arguments": {
      "patient_name": "Nguyễn An",
      "specialty": "Tim mạch",
      "doctor_name": "PGS.TS Nguyễn Hoàng Nam",
      "appointment_datetime": "08:30 20/09/2026",
      "location": "Vinmec Times City",
      "reason": "tôi muốn kiểm tra định kỳ"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "VMC-2026-0830"
    },
    "latency_ms": 459.69
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "output": "Đã đặt lịch khám Vinmec thành công theo bác sĩ và khung giờ đã xác nhận.",
    "latency_ms": 496.18
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật và xác nhận Agent chạy trên Gemini API thật.
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 6 lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Chưa Commit và Push.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân và dán vào ô nộp bài trên hệ thống LMS VLearn.

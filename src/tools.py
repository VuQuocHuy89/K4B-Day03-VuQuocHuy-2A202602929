"""Tool schemas and offline execution backend for the Vinmec Care Coordinator."""

import json
from typing import Any, Dict


# ==============================================================================
# 1. NATIVE JSON SCHEMA TOOL DEFINITIONS
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "doctor_schedule_query",
        "description": "Tra cứu bác sĩ và khung giờ còn trống theo chuyên khoa, cơ sở và ngày mong muốn tại Vinmec.",
        "parameters": {
            "type": "object",
            "properties": {
                "specialty": {
                    "type": "string",
                    "description": "Tên chuyên khoa cần khám, ví dụ 'Tim mạch' hoặc 'Da liễu'.",
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Ngày mong muốn khám theo định dạng DD/MM/YYYY, ví dụ '20/09/2026'.",
                },
                "location": {
                    "type": "string",
                    "description": "Cơ sở Vinmec mong muốn, ví dụ 'Vinmec Times City'.",
                },
                "time_preference": {
                    "type": "string",
                    "description": "Ưu tiên thời gian, có thể là 'buổi sáng', 'buổi chiều' hoặc 'bất kỳ'.",
                },
            },
            "required": ["specialty", "preferred_date", "location", "time_preference"],
        },
    },
    {
        "name": "book_medical_appointment",
        "description": "Đặt lịch khám tại Vinmec sau khi đã xác nhận bác sĩ và khung giờ còn trống.",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Họ tên bệnh nhân.",
                },
                "specialty": {
                    "type": "string",
                    "description": "Chuyên khoa cần khám.",
                },
                "doctor_name": {
                    "type": "string",
                    "description": "Tên bác sĩ được chọn từ kết quả tra cứu lịch.",
                },
                "appointment_datetime": {
                    "type": "string",
                    "description": "Ngày và giờ khám đã xác nhận, ví dụ '08:30 20/09/2026'.",
                },
                "location": {
                    "type": "string",
                    "description": "Cơ sở Vinmec thực hiện lịch khám.",
                },
                "reason": {
                    "type": "string",
                    "description": "Lý do khám do bệnh nhân mô tả ngắn gọn; không dùng để chẩn đoán.",
                },
            },
            "required": [
                "patient_name",
                "specialty",
                "doctor_name",
                "appointment_datetime",
                "location",
                "reason",
            ],
        },
    },
]


# ==============================================================================
# 2. MOCK DATA AND TOOL EXECUTION LAYER
# ==============================================================================

MOCK_CLINIC_DATABASE = {
    "tim mạch": {
        "display_name": "Tim mạch",
        "clinic": "Vinmec Times City",
        "doctors": [
            {
                "doctor_name": "PGS.TS Nguyễn Hoàng Nam",
                "title": "Trưởng khoa Tim mạch",
                "available_slots": ["08:30 20/09/2026", "10:30 20/09/2026"],
            }
        ],
    },
    "da liễu": {
        "display_name": "Da liễu",
        "clinic": "Vinmec Times City",
        "doctors": [
            {
                "doctor_name": "BS.CKII Trần Minh Anh",
                "title": "Bác sĩ Da liễu",
                "available_slots": ["10:00 21/09/2026", "14:00 21/09/2026"],
            }
        ],
    },
    "nhi khoa": {
        "display_name": "Nhi khoa",
        "clinic": "Vinmec Central Park",
        "doctors": [
            {
                "doctor_name": "TS.BS Lê Thu Hà",
                "title": "Bác sĩ Nhi khoa",
                "available_slots": ["09:00 22/09/2026", "15:30 22/09/2026"],
            }
        ],
    },
}


def _normalise(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def execute_doctor_schedule_query(
    specialty: str,
    preferred_date: str,
    location: str = "Vinmec Times City",
    time_preference: str = "bất kỳ",
) -> str:
    """Return matching doctors and appointment slots from the offline clinic database."""
    specialty_key = _normalise(specialty)
    clinic = MOCK_CLINIC_DATABASE.get(specialty_key)
    if not clinic:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Chưa có dữ liệu lịch khám cho chuyên khoa '{specialty}'.",
                "available_specialties": [item["display_name"] for item in MOCK_CLINIC_DATABASE.values()],
            },
            ensure_ascii=False,
        )

    requested_location = _normalise(location)
    if requested_location and requested_location not in _normalise(clinic["clinic"]):
        return json.dumps(
            {
                "status": "NO_AVAILABILITY",
                "specialty": clinic["display_name"],
                "location": location,
                "message": f"Hiện chưa có lịch phù hợp tại {location}. Cơ sở có dữ liệu là {clinic['clinic']}.",
            },
            ensure_ascii=False,
        )

    date_matches = [
        {
            **doctor,
            "available_slots": [slot for slot in doctor["available_slots"] if preferred_date in slot],
        }
        for doctor in clinic["doctors"]
    ]
    time_key = _normalise(time_preference)
    if "sáng" in time_key or "sang" in time_key:
        date_matches = [
            {
                **doctor,
                "available_slots": [slot for slot in doctor["available_slots"] if int(slot[:2]) < 12],
            }
            for doctor in date_matches
        ]
    elif "chiều" in time_key or "chieu" in time_key:
        date_matches = [
            {
                **doctor,
                "available_slots": [slot for slot in doctor["available_slots"] if int(slot[:2]) >= 12],
            }
            for doctor in date_matches
        ]

    date_matches = [doctor for doctor in date_matches if doctor["available_slots"]]
    if not date_matches:
        return json.dumps(
            {
                "status": "NO_AVAILABILITY",
                "specialty": clinic["display_name"],
                "location": clinic["clinic"],
                "preferred_date": preferred_date,
                "message": "Không tìm thấy khung giờ phù hợp với ngày và thời gian ưu tiên.",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "SUCCESS",
            "specialty": clinic["display_name"],
            "location": clinic["clinic"],
            "preferred_date": preferred_date,
            "doctors": date_matches,
            "message": f"Tìm thấy {len(date_matches)} bác sĩ có lịch phù hợp.",
        },
        ensure_ascii=False,
    )


def execute_book_medical_appointment(
    patient_name: str,
    specialty: str,
    doctor_name: str,
    appointment_datetime: str,
    location: str,
    reason: str,
) -> str:
    """Book a validated mock appointment without performing medical diagnosis."""
    clinic = MOCK_CLINIC_DATABASE.get(_normalise(specialty))
    if not clinic:
        return json.dumps(
            {"status": "NOT_FOUND", "message": f"Chưa hỗ trợ chuyên khoa '{specialty}'."},
            ensure_ascii=False,
        )

    matching_doctor = next(
        (doctor for doctor in clinic["doctors"] if _normalise(doctor["doctor_name"]) == _normalise(doctor_name)),
        None,
    )
    if not matching_doctor or appointment_datetime not in matching_doctor["available_slots"]:
        return json.dumps(
            {
                "status": "NO_AVAILABILITY",
                "message": "Bác sĩ hoặc khung giờ không còn trong lịch đã tra cứu; chưa tạo booking.",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "SUCCESS",
            "booking_id": f"VMC-{appointment_datetime[-4:]}-{appointment_datetime.split()[0].replace(':', '')}",
            "patient_name": patient_name,
            "specialty": clinic["display_name"],
            "doctor_name": matching_doctor["doctor_name"],
            "appointment_datetime": appointment_datetime,
            "location": clinic["clinic"],
            "reason": reason,
            "message": f"Đặt lịch thành công cho {patient_name} với {matching_doctor['doctor_name']} vào lúc {appointment_datetime} tại {clinic['clinic']}.",
        },
        ensure_ascii=False,
    )


TOOL_ROUTER = {
    "doctor_schedule_query": execute_doctor_schedule_query,
    "book_medical_appointment": execute_book_medical_appointment,
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Route a native tool call to the corresponding execution function."""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as exc:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(exc)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.booking_service import save_booking

router = APIRouter()

class BookingRequest(BaseModel):
    name: str
    slot: str
    phone: str

@router.post("/book-slot")
async def book_slot(payload: BookingRequest):

    print("🔥 /book-slot endpoint was called!")       # <--- HERE
    print("Booking Payload:", payload.dict())        # <--- SEE FULL DATA

    appt_id = await save_booking(
        name=payload.name,
        slot=payload.slot,
        phone=payload.phone
    )

    return {
        "success": True,
        "appointment_id": appt_id,
        "message": f"Appointment booked for {payload.slot}"
    }

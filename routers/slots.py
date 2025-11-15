from fastapi import APIRouter

router = APIRouter()

@router.get("/available-slots")
async def available_slots():
    # Temporary static response
    # Later we will fetch from DB
    return {
        "slots": [
            "10:00 AM",
            "11:00 AM",
            "12:00 PM",
        ]
    }

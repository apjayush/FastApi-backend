from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_db_connection
from datetime import date
from dotenv import load_dotenv
import os

router = APIRouter()

load_dotenv()
DB_SCHEMA = os.getenv("DB_SCHEMA", "healthcare").strip()
# MAX_CAPACITY = int(os.getenv("MAX_CAPACITY", 4))
# DEFAULT_SLOTS = os.getenv("DEFAULT_SLOTS", "11AM,12PM,1PM").split(",")

# ...existing code...

# --------- TEST RIDE REQUEST MODEL ----------
class TestRideRequest(BaseModel):
    name: str
    phone: str
    vehicle: str = None  # Optional: if user selected a vehicle

@router.post("/book-test-ride")
async def book_test_ride(payload: TestRideRequest):
    """
    Book a test ride
    """
    name = payload.name.strip()
    phone = payload.phone.strip()
    vehicle = payload.vehicle
    today = date.today()

    print(f"Booking test ride for {name} ({phone}) - Vehicle: {vehicle}")

    try:
        conn = await get_db_connection()

        # Insert test ride booking
        insert_query = f"""
            INSERT INTO {DB_SCHEMA}.test_rides (name, phone, vehicle, booking_date, status)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        test_ride_id = await conn.fetchval(
            insert_query,
            name,
            phone,
            vehicle or "Not specified",
            today,
            "pending"
        )

        await conn.close()

        print(f"✅ Test ride booked with ID: {test_ride_id}")

        return {
            "status": "success",
            "test_ride_id": test_ride_id,
            "message": f"Test ride booked for {name}",
            "name": name,
            "phone": phone,
            "vehicle": vehicle
        }

    except Exception as e:
        print(f"❌ Error booking test ride: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")
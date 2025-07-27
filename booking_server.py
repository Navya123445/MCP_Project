# booking_server.py ─ corrected version with upselling reservation functionality
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
import numpy as np
from typing import Union, Optional
from datetime import datetime
import uvicorn, json

app = FastAPI(
    title="Hotel Booking Server",
    description="Hotel Room Booking Management API"
)

CSV_PATH = "Hotel_data_updated.csv"
COLUMN_ORDER = [
    "Room Number",
    "Room Type",
    "Availability",
    "Name of Guest",
    "Number of People",
    "Extra Facility",
    "Check-in Date",
    "Check-out Date",
    "Price",
    "reserved for upselling/season"
]

# ── load CSV ────────────────────────────────────────────────────────────
try:
    df = pd.read_csv(CSV_PATH)
    df["Room Number"]      = df["Room Number"].astype(int)
    df["Price"]            = df["Price"].astype(float)
    df["Name of Guest"]    = df["Name of Guest"].fillna("").astype(str)
    df["Room Type"]        = df["Room Type"].astype(str)
    df["Availability"]     = df["Availability"].fillna("Available").astype(str)
    df["Number of People"] = df["Number of People"].fillna("").astype(str)
    df["Extra Facility"]   = df["Extra Facility"].fillna("").astype(str)
    df["Check-in Date"]    = df["Check-in Date"].fillna("").astype(str)
    df["Check-out Date"]   = df["Check-out Date"].fillna("").astype(str)
    df["reserved for upselling/season"] = df["reserved for upselling/season"].fillna("No").astype(str)
    df = df.replace([np.inf, -np.inf], 0).fillna("")
except FileNotFoundError:
    df = pd.DataFrame(columns=COLUMN_ORDER)

def _json_ready(records):
    rows = []
    for rec in records:
        clean = {}
        for k, v in rec.items():
            if pd.isna(v):
                clean[k] = ""
            elif k == "Price":
                clean[k] = float(v)
            elif isinstance(v, (np.integer, int)):
                clean[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                clean[k] = float(v)
            else:
                clean[k] = str(v)
        rows.append(clean)
    return rows

def _save_csv():
    df.to_csv(CSV_PATH, index=False, columns=COLUMN_ORDER)

# ── models ──────────────────────────────────────────────────────────────
class BookingRequest(BaseModel):
    guest_id: int
    room_number: int
    check_in_date: str
    check_out_date: str
    number_of_adults: int
    purpose_of_visit: str

class BookingResponse(BaseModel):
    booking_id: str
    guest_id: int
    room_number: int
    room_type: str
    check_in_date: str
    check_out_date: str
    number_of_adults: int
    purpose_of_visit: str
    total_cost: float
    booking_status: str

class RoomUpdate(BaseModel):
    room_number: int
    availability: str
    guest_name: str = ""
    number_of_people: Union[int, str] = ""
    check_in_date: str = ""
    check_out_date: str = ""
    extra_facility: str = ""
    class Config:
        extra = "allow"

# ── endpoints ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Hotel Booking Server is running", "total_rooms": len(df)}

@app.get("/rooms/available")
async def available_rooms():
    """Get available rooms excluding reserved rooms for regular guests"""
    rooms = df[(df["Availability"].str.lower() == "available") & 
               (df["reserved for upselling/season"].str.lower() == "no")]
    return _json_ready(rooms.to_dict("records"))

@app.get("/rooms/available-for-dates")
async def available_rooms_for_dates(check_in: str = Query(...), check_out: str = Query(...)):
    """Get rooms available for specific date range excluding reserved rooms for regular guests"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        
        available_rooms = []
        
        for _, room in df.iterrows():
            # Skip reserved rooms for regular guest queries
            if room['reserved for upselling/season'].lower() == 'yes':
                continue
                
            room_available = True
            
            # Check if room is currently available
            if room['Availability'].lower() == 'available':
                available_rooms.append(room.to_dict())
                continue
            
            # Check if room will be free by check-in date
            if room['Check-out Date']:
                try:
                    room_checkout = datetime.strptime(room['Check-out Date'], '%Y-%m-%d')
                    if room_checkout <= check_in_date:
                        # Room will be free before guest check-in
                        available_rooms.append(room.to_dict())
                except:
                    pass
        
        return _json_ready(available_rooms)
        
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(500, f"Error processing dates: {str(e)}")

@app.get("/rooms/available-with-upselling")
async def available_rooms_with_upselling(markup_percentage: float = Query(15.0)):
    """Get all available rooms including reserved rooms with markup for upselling"""
    available_rooms = df[df["Availability"].str.lower() == "available"]
    
    rooms_with_upselling = []
    for _, room in available_rooms.iterrows():
        room_dict = room.to_dict()
        
        # Apply markup to reserved rooms
        if room['reserved for upselling/season'].lower() == 'yes':
            original_price = float(room['Price'])
            markup_price = original_price * (1 + markup_percentage / 100)
            room_dict['Price'] = markup_price
            room_dict['original_price'] = original_price
            room_dict['is_premium_upselling'] = True
            room_dict['markup_percentage'] = markup_percentage
        else:
            room_dict['is_premium_upselling'] = False
            room_dict['original_price'] = float(room['Price'])
            room_dict['markup_percentage'] = 0
    
        rooms_with_upselling.append(room_dict)
    
    return _json_ready(rooms_with_upselling)

@app.get("/rooms/available-for-dates-with-upselling")
async def available_rooms_for_dates_with_upselling(
    check_in: str = Query(...), 
    check_out: str = Query(...),
    markup_percentage: float = Query(15.0)
):
    """Get rooms available for specific date range including reserved rooms with markup"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        
        available_rooms = []
        
        for _, room in df.iterrows():
            room_available = True
            
            # Check if room is currently available
            if room['Availability'].lower() == 'available':
                room_dict = room.to_dict()
                
                # Apply markup to reserved rooms
                if room['reserved for upselling/season'].lower() == 'yes':
                    original_price = float(room['Price'])
                    markup_price = original_price * (1 + markup_percentage / 100)
                    room_dict['Price'] = markup_price
                    room_dict['original_price'] = original_price
                    room_dict['is_premium_upselling'] = True
                    room_dict['markup_percentage'] = markup_percentage
                else:
                    room_dict['is_premium_upselling'] = False
                    room_dict['original_price'] = float(room['Price'])
                    room_dict['markup_percentage'] = 0
                
                available_rooms.append(room_dict)
                continue
            
            # Check if room will be free by check-in date
            if room['Check-out Date']:
                try:
                    room_checkout = datetime.strptime(room['Check-out Date'], '%Y-%m-%d')
                    if room_checkout <= check_in_date:
                        room_dict = room.to_dict()
                        
                        # Apply markup to reserved rooms
                        if room['reserved for upselling/season'].lower() == 'yes':
                            original_price = float(room['Price'])
                            markup_price = original_price * (1 + markup_percentage / 100)
                            room_dict['Price'] = markup_price
                            room_dict['original_price'] = original_price
                            room_dict['is_premium_upselling'] = True
                            room_dict['markup_percentage'] = markup_percentage
                        else:
                            room_dict['is_premium_upselling'] = False
                            room_dict['original_price'] = float(room['Price'])
                            room_dict['markup_percentage'] = 0
                        
                        available_rooms.append(room_dict)
                except:
                    pass
        
        return _json_ready(available_rooms)
        
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(500, f"Error processing dates: {str(e)}")

@app.get("/rooms/reserved-for-upselling")
async def get_reserved_rooms():
    """Get rooms reserved for upselling/seasonal pricing - Staff only"""
    reserved_rooms = df[df["reserved for upselling/season"].str.lower() == "yes"]
    return _json_ready(reserved_rooms.to_dict("records"))

@app.get("/rooms/all-for-staff")
async def all_rooms_for_staff():
    """Get all rooms including reserved ones - Staff interface only"""
    return _json_ready(df.to_dict("records"))

@app.get("/rooms/by-type/{room_type}")
async def rooms_by_type(room_type: str):
    rooms = df[df["Room Type"].str.lower() == room_type.lower()]
    if rooms.empty:
        raise HTTPException(404, f"No {room_type} rooms found")
    return _json_ready(rooms.to_dict("records"))

@app.get("/rooms/details/{room_number}")
async def room_details(room_number: int):
    row = df[df["Room Number"] == room_number]
    if row.empty:
        raise HTTPException(404, f"Room {room_number} not found")
    return _json_ready([row.iloc[0].to_dict()])[0]

@app.get("/rooms/check-availability/{room_number}")
async def room_availability(room_number: int):
    row = df[df["Room Number"] == room_number]
    if row.empty:
        raise HTTPException(404, f"Room {room_number} not found")
    data = row.iloc[0]
    available = data["Availability"].lower() == "available"
    return {
        "room_number": room_number,
        "available": available,
        "room_type": data["Room Type"],
        "price": float(data["Price"]),
        "availability_status": data["Availability"],
        "current_guest": data["Name of Guest"] if not available else None,
        "reserved_for_upselling": data["reserved for upselling/season"]
    }

@app.get("/rooms/price/{room_number}")
async def room_price(room_number: int):
    row = df[df["Room Number"] == room_number]
    if row.empty:
        raise HTTPException(404, f"Room {room_number} not found")
    data = row.iloc[0]
    return {
        "room_number": room_number,
        "room_type": data["Room Type"],
        "price": float(data["Price"]),
        "extra_facilities": data["Extra Facility"] or "None",
        "reserved_for_upselling": data["reserved for upselling/season"]
    }

@app.get("/rooms/by-price-range")
async def rooms_by_price(min_price: float, max_price: float):
    rooms = df[(df["Price"] >= min_price) & (df["Price"] <= max_price)]
    return _json_ready(rooms.to_dict("records"))

@app.post("/bookings/create")
async def create_booking(booking: BookingRequest):
    row = df[df["Room Number"] == booking.room_number]
    if row.empty:
        raise HTTPException(404, f"Room {booking.room_number} not found")
    if row.iloc[0]["Availability"].lower() != "available":
        raise HTTPException(400, "Room is not available")

    df.loc[df["Room Number"] == booking.room_number,
           ["Availability", "Name of Guest", "Check-in Date", "Check-out Date"]] = [
               "Booked", f"Guest_{booking.guest_id}", booking.check_in_date, booking.check_out_date]

    nights = (
        datetime.strptime(booking.check_out_date, "%Y-%m-%d")
        - datetime.strptime(booking.check_in_date, "%Y-%m-%d")
    ).days
    cost = float(row.iloc[0]["Price"]) * nights
    booking_id = f"BK{booking.guest_id}{booking.room_number}{datetime.now().strftime('%Y%m%d%H%M')}"

    _save_csv()
    return BookingResponse(
        booking_id=booking_id,
        guest_id=booking.guest_id,
        room_number=booking.room_number,
        room_type=row.iloc[0]["Room Type"],
        check_in_date=booking.check_in_date,
        check_out_date=booking.check_out_date,
        number_of_adults=booking.number_of_adults,
        purpose_of_visit=booking.purpose_of_visit,
        total_cost=cost,
        booking_status="Confirmed",
    )

@app.put("/rooms/{room_number}/update-guest-info")
async def update_guest(room_number: int, payload: RoomUpdate):
    row = df[df["Room Number"] == room_number]
    if row.empty:
        raise HTTPException(404, f"Room {room_number} not found")

    df.loc[df["Room Number"] == room_number, [
        "Availability",
        "Name of Guest",
        "Number of People",
        "Extra Facility",
        "Check-in Date",
        "Check-out Date",
    ]] = [
        payload.availability or row.iloc[0]["Availability"],
        payload.guest_name or row.iloc[0]["Name of Guest"],
        str(payload.number_of_people) or row.iloc[0]["Number of People"],
        payload.extra_facility or row.iloc[0]["Extra Facility"],
        payload.check_in_date or row.iloc[0]["Check-in Date"],
        payload.check_out_date or row.iloc[0]["Check-out Date"],
    ]
    _save_csv()
    return {"message": f"Room {room_number} updated"}

@app.put("/rooms/{room_number}/status")
async def update_status(room_number: int, payload: RoomUpdate):
    return await update_guest(room_number, payload)

@app.delete("/bookings/cancel/{room_number}")
async def cancel_booking(room_number: int):
    row = df[df["Room Number"] == room_number]
    if row.empty:
        raise HTTPException(404, f"Room {room_number} not found")
    df.loc[df["Room Number"] == room_number, [
        "Availability",
        "Name of Guest",
        "Number of People",
        "Extra Facility",
        "Check-in Date",
        "Check-out Date",
    ]] = ["Available", "", "", "", "", ""]
    _save_csv()
    return {"message": f"Booking cancelled for room {room_number}"}

@app.get("/bookings/occupied-rooms")
async def occupied_rooms():
    occupied = df[df["Availability"].str.lower() == "booked"]
    return _json_ready(occupied.to_dict("records"))

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8002)

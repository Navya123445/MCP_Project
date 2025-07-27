# guest_profile_server.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
from typing import Optional
import uvicorn

app = FastAPI(title="Guest Profile Server", description="Hotel Guest Profile Management API")

# Load guest data
try:
    # Convert your updated_sample_data.xlsx to CSV first
    df = pd.read_csv("Guest_profile_data.csv")
    print(f"Loaded {len(df)} guest profiles")
except FileNotFoundError:
    print("Guest_profile_data.csv not found. Please convert updated_sample_data.xlsx to CSV")
    df = pd.DataFrame()

class GuestProfile(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    gender: str
    phone_number: str
    preferred_language: str
    check_in_date: str
    purpose_of_visit: str
    Stay_days_number: int
    room_number: str
    place_of_origin: str
    room_type: str
    special_requests: str
    amenities_used: str
    profession: str
    extra_activities_booked: str
    loyalty_member: str
    payment_method: str
    total_bill: float
    feedback_and_issues: str = ""

@app.get("/")
async def root():
    return {"message": "Guest Profile Server is running", "total_guests": len(df)}

@app.get("/guest/by-id/{guest_id}")
async def get_guest_by_id(guest_id: int):
    """Get guest profile by ID"""
    guest = df[df['id'] == guest_id]
    if guest.empty:
        raise HTTPException(status_code=404, detail=f"Guest with ID {guest_id} not found")
    
    return guest.iloc[0].to_dict()

@app.get("/guest/by-name")
async def get_guest_by_name(first_name: str = Query(...), last_name: str = Query(...)):
    """Get guest profile by name"""
    guest = df[(df['first_name'].str.lower() == first_name.lower()) & 
               (df['last_name'].str.lower() == last_name.lower())]
    if guest.empty:
        raise HTTPException(status_code=404, detail=f"Guest {first_name} {last_name} not found")
    
    return guest.iloc[0].to_dict()

@app.get("/guest/by-phone/{phone_number}")
async def get_guest_by_phone(phone_number: str):
    """Get guest profile by phone number"""
    guest = df[df['phone_number'].astype(str) == phone_number]
    if guest.empty:
        raise HTTPException(status_code=404, detail=f"Guest with phone {phone_number} not found")
    
    return guest.iloc[0].to_dict()

@app.get("/guest/preferences/{guest_id}")
async def get_guest_preferences(guest_id: int):
    """Get guest preferences"""
    guest = df[df['id'] == guest_id]
    if guest.empty:
        raise HTTPException(status_code=404, detail=f"Guest with ID {guest_id} not found")
    
    guest_data = guest.iloc[0]
    preferences = {
        "guest_id": guest_id,
        "preferred_language": guest_data.get('preferred_language', ''),
        "room_type": guest_data.get('room_type', ''),
        "special_requests": guest_data.get('special_requests', ''),
        "amenities_used": guest_data.get('amenities_used', ''),
        "extra_activities_booked": guest_data.get('extra_activities_booked', ''),
        "loyalty_status": guest_data.get('loyalty_member', 'New')
    }
    
    return preferences

@app.get("/guest/history/{guest_id}")
async def get_guest_history(guest_id: int):
    """Get guest stay history"""
    guest = df[df['id'] == guest_id]
    if guest.empty:
        raise HTTPException(status_code=404, detail=f"Guest with ID {guest_id} not found")
    
    guest_data = guest.iloc[0]
    history = {
        "guest_id": guest_id,
        "previous_stays": guest_data.get('Stay_days_number', 0),
        "last_check_in": guest_data.get('check_in_date', ''),
        "last_room_type": guest_data.get('room_type', ''),
        "total_spending": guest_data.get('total_bill', 0),
        "feedback": guest_data.get('Feedback and issues raised', 'No feedback'),
        "loyalty_status": guest_data.get('loyalty_member', 'New'),
        "preferred_payment": guest_data.get('payment_method', '')
    }
    
    return history

@app.get("/guests/all")
async def get_all_guests():
    """Get all guest profiles"""
    return df.to_dict('records')

@app.get("/guests/by-loyalty/{loyalty_status}")
async def get_guests_by_loyalty(loyalty_status: str):
    """Get guests by loyalty status"""
    guests = df[df['loyalty_member'].str.lower() == loyalty_status.lower()]
    return guests.to_dict('records')

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)

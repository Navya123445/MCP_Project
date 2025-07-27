# fix_hotel_rooms_complete.py
import pandas as pd
import numpy as np

def fix_hotel_rooms_complete():
    """Complete fix for all hotel room data issues"""
    
    print("🔧 Comprehensive Hotel Room Data Fix...")
    
    # Load the data
    df = pd.read_csv('Hotel_rooms.csv')
    print(f"📊 Original data: {df.shape}")
    
    # Fix 1: Set correct pricing based on room type
    print("💰 Fixing pricing inconsistencies...")
    price_map = {
        'Single': 2000.0,
        'Double': 3500.0,
        'Family': 10000.0,
        'Deluxe': 5000.0,
        'Suite': 8000.0
    }
    
    # Apply correct pricing
    for room_type, correct_price in price_map.items():
        mask = df['Room Type'] == room_type
        df.loc[mask, 'Price'] = correct_price
        count = mask.sum()
        print(f"   ✅ Fixed {count} {room_type} rooms → ₹{correct_price:,.0f}")
    
    # Fix 2: Fix Availability logic
    print("🏨 Fixing availability logic...")
    
    def determine_availability(row):
        # If guest is present and it's not explicitly Available, it's Booked
        if pd.notna(row['Name of Guest']) and row['Name of Guest'] != '':
            if row['Name of Guest'].startswith('Guest_'):
                return 'Booked'
        # If no guest, it's Available
        return 'Available'
    
    # Apply availability logic
    df['Availability'] = df.apply(determine_availability, axis=1)
    
    # Fix contradictions: Available rooms should not have guests
    available_mask = df['Availability'] == 'Available'
    df.loc[available_mask, 'Name of Guest'] = ''
    df.loc[available_mask, 'Number of People'] = ''
    df.loc[available_mask, 'Extra Facility'] = ''
    df.loc[available_mask, 'Check-in Date'] = ''
    
    print(f"   ✅ Available rooms: {(df['Availability'] == 'Available').sum()}")
    print(f"   ✅ Booked rooms: {(df['Availability'] == 'Booked').sum()}")
    
    # Fix 3: Clean data types and missing values
    print("🔧 Fixing data types...")
    
    # Fix Number of People
    df['Number of People'] = df['Number of People'].fillna('')
    df['Number of People'] = df['Number of People'].astype(str).replace('nan', '').replace('4.0', '4').replace('3.0', '3').replace('2.0', '2').replace('1.0', '1')
    
    # Fix other string columns
    df['Name of Guest'] = df['Name of Guest'].fillna('')
    df['Extra Facility'] = df['Extra Facility'].fillna('')
    df['Check-in Date'] = df['Check-in Date'].fillna('')
    
    # Ensure numeric columns are proper types
    df['Room Number'] = df['Room Number'].astype(int)
    df['Price'] = df['Price'].astype(float)
    
    # Fix 4: Remove any remaining problematic values
    df = df.replace([np.inf, -np.inf], 0)
    df = df.fillna('')
    
    # Save fixed data
    df.to_csv('Hotel_rooms.csv', index=False)
    
    print("✅ Hotel room data fixes completed!")
    
    # Verification
    print("\n🔍 Verification Summary:")
    print(f"📊 Total rooms: {len(df)}")
    print(f"🟢 Available: {(df['Availability'] == 'Available').sum()}")
    print(f"🔴 Booked: {(df['Availability'] == 'Booked').sum()}")
    print(f"💰 Price range: ₹{df['Price'].min():,.0f} - ₹{df['Price'].max():,.0f}")
    
    # Show room type distribution
    print("\n🏠 Room Type & Pricing:")
    room_summary = df.groupby(['Room Type', 'Price']).size().reset_index(name='Count')
    for _, row in room_summary.iterrows():
        print(f"   {row['Room Type']}: ₹{row['Price']:,.0f} ({row['Count']} rooms)")
    
    # Test JSON serialization
    print("\n🧪 Testing JSON serialization...")
    try:
        import json
        
        # Test available rooms (critical for booking system)
        available_rooms = df[df['Availability'] == 'Available'].to_dict('records')
        json.dumps(available_rooms)
        print(f"✅ Available rooms JSON: PASSED ({len(available_rooms)} rooms)")
        
        # Test all rooms
        all_rooms = df.to_dict('records')
        json.dumps(all_rooms)
        print(f"✅ All rooms JSON: PASSED ({len(all_rooms)} rooms)")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON test FAILED: {e}")
        return False

if __name__ == "__main__":
    if fix_hotel_rooms_complete():
        print("\n🎉 HOTEL ROOM DATA READY!")
        print("Your booking server should work perfectly now.")
    else:
        print("\n⚠️ Additional fixes needed")

# test_correct_logic.py
import pandas as pd
import requests

def test_correct_availability():
    print("🧪 Testing CORRECT Availability Logic")
    print("=" * 40)
    
    # Test CSV with correct logic
    df = pd.read_csv('Hotel_rooms.csv')
    
    # CORRECT METHOD: Use Availability column
    available_rooms_correct = df[df['Availability'].str.lower() == 'available']
    correct_count = len(available_rooms_correct)
    
    print(f"✅ CORRECT (Availability column): {correct_count} available rooms")
    print(f"   Room numbers: {available_rooms_correct['Room Number'].tolist()}")
    
    # Test API
    try:
        response = requests.get("http://localhost:8002/rooms/available")
        if response.status_code == 200:
            api_rooms = response.json()
            api_count = len(api_rooms)
            print(f"📡 API result: {api_count} available rooms")
            
            if api_count == correct_count:
                print("🎉 SUCCESS: API matches CSV using correct logic!")
            else:
                print("❌ MISMATCH: API needs to be fixed to use Availability column")
        else:
            print(f"❌ API error: {response.status_code}")
    except Exception as e:
        print(f"❌ API error: {e}")

if __name__ == "__main__":
    test_correct_availability()

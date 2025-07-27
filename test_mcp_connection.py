# simple_system_test.py - BASIC HOTEL SYSTEM TEST
import requests
import asyncio
import httpx
from datetime import datetime, timedelta

async def test_hotel_system():
    """Simple test for hotel system functionality"""
    
    print("🏨 SIMPLE HOTEL SYSTEM TEST")
    print("="*40)
    
    # Server URLs
    guest_server = "http://localhost:8001"
    booking_server = "http://localhost:8002"
    mcp_server = "http://localhost:8003"
    
    passed_tests = 0
    total_tests = 6
    
    # Test 1: Server Connectivity
    print("\n1. 🔗 Testing Server Connectivity...")
    try:
        guest_ok = requests.get(f"{guest_server}/", timeout=5).status_code == 200
        booking_ok = requests.get(f"{booking_server}/", timeout=5).status_code == 200
        mcp_ok = requests.get(f"{mcp_server}/", timeout=5).status_code == 200
        
        if guest_ok and booking_ok and mcp_ok:
            print("   ✅ All servers connected")
            passed_tests += 1
        else:
            print("   ❌ Some servers not responding")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Test 2: Guest Profile
    print("\n2. 👤 Testing Guest Profile...")
    try:
        response = requests.get(f"{guest_server}/guest/by-id/1", timeout=5)
        if response.status_code == 200:
            guest = response.json()
            print(f"   ✅ Found guest: {guest.get('first_name')} {guest.get('last_name')}")
            passed_tests += 1
        else:
            print("   ❌ Guest profile failed")
    except Exception as e:
        print(f"   ❌ Guest test failed: {e}")
    
    # Test 3: Room Operations
    print("\n3. 🏨 Testing Room Operations...")
    try:
        response = requests.get(f"{booking_server}/rooms/available", timeout=5)
        if response.status_code == 200:
            rooms = response.json()
            print(f"   ✅ Found {len(rooms)} available rooms")
            passed_tests += 1
        else:
            print("   ❌ Room operations failed")
    except Exception as e:
        print(f"   ❌ Room test failed: {e}")
    
    # Test 4: MCP Tools
    print("\n4. 🤖 Testing MCP Tools...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{mcp_server}/sse",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                print(f"   ✅ Found {len(tools)} MCP tools")
                passed_tests += 1
            else:
                print("   ❌ MCP tools failed")
    except Exception as e:
        print(f"   ❌ MCP test failed: {e}")
    
    # Test 5: Guest Profile via MCP
    print("\n5. 🧠 Testing MCP Guest Profile...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{mcp_server}/sse",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_contextual_guest_profile",
                        "arguments": {"guest_id": 1}
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("result", {}).get("success"):
                    print("   ✅ MCP guest profile working")
                    passed_tests += 1
                else:
                    print("   ❌ MCP guest profile failed")
            else:
                print("   ❌ MCP guest profile failed")
    except Exception as e:
        print(f"   ❌ MCP guest test failed: {e}")
    
    # Test 6: Simple Booking Test
    print("\n6. 📋 Testing Basic Booking...")
    try:
        # Get available room
        rooms_response = requests.get(f"{booking_server}/rooms/available", timeout=5)
        if rooms_response.status_code == 200 and rooms_response.json():
            room = rooms_response.json()[0]
            room_number = int(room.get('Room Number', 101))
            
            # Try booking via MCP
            async with httpx.AsyncClient() as client:
                booking_response = await client.post(
                    f"{mcp_server}/sse",
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "contextual_room_booking",
                            "arguments": {
                                "guest_id": 1,
                                "room_number": room_number,
                                "check_in_date": str(datetime.now().date() + timedelta(days=1)),
                                "check_out_date": str(datetime.now().date() + timedelta(days=3)),
                                "number_of_adults": 2
                            }
                        }
                    },
                    timeout=15.0
                )
                
                if booking_response.status_code == 200:
                    result = booking_response.json()
                    if result.get("result", {}).get("success"):
                        print(f"   ✅ Booking successful for room {room_number}")
                        passed_tests += 1
                    else:
                        print("   ❌ Booking failed")
                else:
                    print("   ❌ Booking request failed")
        else:
            print("   ❌ No rooms available for booking test")
    except Exception as e:
        print(f"   ❌ Booking test failed: {e}")
    
    # Final Results
    print("\n" + "="*40)
    print(f"🎯 RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is working!")
    elif passed_tests >= 4:
        print("✅ MOSTLY WORKING! Minor issues.")
    elif passed_tests >= 2:
        print("⚠️ PARTIALLY WORKING! Check system.")
    else:
        print("❌ SYSTEM ISSUES! Major problems detected.")
    
    print("="*40)

if __name__ == "__main__":
    try:
        asyncio.run(test_hotel_system())
    except KeyboardInterrupt:
        print("\n⏹️ Test stopped by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")

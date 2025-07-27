# sse_client_agent.py - SSE-BASED MCP CLIENT FOR WINDOWS
import asyncio
import logging
import json
import requests
import httpx
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hotel-sse-client")

class HotelSSEClient:
    def __init__(self):
        self.base_url = "http://localhost:8003"
        self.sse_endpoint = f"{self.base_url}/sse"
        self.available_tools = []
        self.conversation_history = {}
        self.session_id = None
        logger.info("🤖 Hotel SSE Client initialized")
    
    async def connect(self):
        """Connect to SSE MCP server"""
        try:
            logger.info("🔗 Connecting to Hotel SSE Server...")
            
            # Test basic connectivity
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/", timeout=10.0)
                
                if response.status_code == 200:
                    logger.info("✅ Server reachable")
                    
                    # Initialize session and get tools
                    init_response = await client.post(
                        self.sse_endpoint,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {
                                    "name": "hotel-sse-client",
                                    "version": "1.0.0"
                                }
                            }
                        },
                        timeout=15.0
                    )
                    
                    if init_response.status_code == 200:
                        logger.info("✅ Session initialized")
                        
                        # Get available tools
                        tools_response = await client.post(
                            self.sse_endpoint,
                            json={
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/list",
                                "params": {}
                            },
                            timeout=10.0
                        )
                        
                        if tools_response.status_code == 200:
                            tools_data = tools_response.json()
                            if "result" in tools_data and "tools" in tools_data["result"]:
                                self.available_tools = tools_data["result"]["tools"]
                                tool_names = [tool["name"] for tool in self.available_tools]
                                logger.info(f"✅ SSE Connected! Available tools: {tool_names}")
                                return True
                            else:
                                # Fallback: assume basic tools are available
                                self.available_tools = [
                                    {"name": "get_guest_profile"},
                                    {"name": "get_available_rooms"},
                                    {"name": "book_room"}
                                ]
                                logger.info("✅ SSE Connected with fallback tools!")
                                return True
                        else:
                            logger.warning("⚠️ Tools list failed, using fallback")
                            self.available_tools = [
                                {"name": "get_guest_profile"},
                                {"name": "get_available_rooms"},
                                {"name": "book_room"}
                            ]
                            return True
                else:
                    logger.error(f"❌ Server not reachable: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ SSE Connection failed: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call SSE MCP tool"""
        try:
            logger.info(f"🔧 Calling SSE tool: {tool_name} with {arguments}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.sse_endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    if "result" in result_data:
                        tool_result = result_data["result"]
                        logger.info(f"✅ SSE Tool result: {tool_result}")
                        return tool_result
                    elif "error" in result_data:
                        error_msg = result_data["error"]
                        logger.error(f"❌ SSE Tool error: {error_msg}")
                        return {"error": str(error_msg)}
                    else:
                        logger.warning("⚠️ Unexpected response format")
                        return {"error": "Unexpected response format"}
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ SSE Tool call failed: {error_msg}")
                    return {"error": error_msg}
                    
        except Exception as e:
            logger.error(f"❌ SSE Tool call error: {e}")
            return {"error": str(e)}
    
    async def chat(self, message: str, context: Dict = None, session_id: str = "default") -> Dict[str, Any]:
        """Enhanced chat with SSE integration"""
        
        # Initialize session history
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({"role": "user", "content": message})
        
        try:
            # Guest identification
            if context and (context.get('guest_name') or context.get('guest_id')):
                return await self._handle_guest_identification(message, context, session_id)
            
            # Booking requests
            elif any(word in message.lower() for word in ['book', 'booking', 'reserve']):
                return await self._handle_booking_request(message, context, session_id)
            
            # Room availability
            elif any(word in message.lower() for word in ['available', 'rooms', 'show rooms']):
                return await self._handle_room_request(message, context, session_id)
            
            # Default response
            else:
                response = """Hello! I'm your AI-powered hotel assistant with SSE integration. I can help you with:

🏨 **Room Booking** - Find and book available rooms
👤 **Guest Profiles** - Look up your personalized information  
💎 **Recommendations** - Get tailored suggestions
🔍 **Room Details** - Check specific room information

What would you like to do today?"""
                
                self.conversation_history[session_id].append({"role": "assistant", "content": response})
                return {"response": response}
                
        except Exception as e:
            logger.error(f"❌ Chat error: {e}")
            error_response = "I'm having trouble processing your request. Please try again."
            self.conversation_history[session_id].append({"role": "assistant", "content": error_response})
            return {"response": error_response}
    
    async def _handle_guest_identification(self, message: str, context: Dict, session_id: str) -> Dict[str, Any]:
        """Handle guest profile lookup"""
        try:
            # Prepare arguments for SSE tool
            if context.get('guest_id'):
                args = {"guest_id": context['guest_id']}
            elif context.get('guest_name'):
                name_parts = context['guest_name'].split()
                args = {"first_name": name_parts[0], "last_name": " ".join(name_parts[1:])}
            else:
                return {"response": "Please provide your guest ID or full name."}
            
            # Call SSE tool
            result = await self.call_tool("get_guest_profile", args)
            
            if result.get("success") and result.get("guest_profile"):
                guest = result["guest_profile"]
                
                response = f"""Welcome back, {guest['first_name']} {guest['last_name']}! 🎉

**Your Profile:**
- **ID:** {guest['id']}
- **Loyalty Status:** {guest.get('loyalty_member', 'New')} Member
- **From:** {guest.get('place_of_origin', 'Not specified')}
- **Total Spending:** ₹{guest.get('total_bill', 0):,}
- **Previous Room:** {guest.get('room_type', 'First visit')}

I can now provide personalized recommendations and help you book rooms! What would you like to do?"""
                
                self.conversation_history[session_id].append({"role": "assistant", "content": response})
                return {
                    "response": response, 
                    "guest_profile": guest,
                    "tools_used": ["get_guest_profile"]
                }
            else:
                error_response = f"I couldn't find your profile. Please check your information."
                self.conversation_history[session_id].append({"role": "assistant", "content": error_response})
                return {"response": error_response}
                
        except Exception as e:
            logger.error(f"Guest identification error: {e}")
            return {"response": "Error looking up your profile. Please try again."}
    
    async def _handle_booking_request(self, message: str, context: Dict, session_id: str) -> Dict[str, Any]:
        """Handle room booking with SSE tools"""
        try:
            # Check if we have guest profile
            guest_profile = context.get('guest_profile') if context else None
            if not guest_profile:
                return {"response": "Please identify yourself first before booking a room."}
            
            # Extract booking details (simplified)
            import re
            room_match = re.search(r'room\s*(\d+)', message.lower())
            if not room_match:
                # Show available rooms first
                return await self._handle_room_request(message, context, session_id)
            
            room_number = int(room_match.group(1))
            
            # Simple date handling (you can enhance this)
            from datetime import datetime, timedelta
            check_in = str(datetime.now().date() + timedelta(days=1))
            check_out = str(datetime.now().date() + timedelta(days=3))
            
            # Extract adults
            adults_match = re.search(r'(\d+)\s*adults?', message.lower())
            adults = int(adults_match.group(1)) if adults_match else 2
            
            # **CRITICAL: Call SSE booking tool**
            booking_args = {
                "guest_id": guest_profile['id'],
                "room_number": room_number,
                "check_in_date": check_in,
                "check_out_date": check_out,
                "number_of_adults": adults,
                "purpose_of_visit": guest_profile.get('purpose_of_visit', 'Leisure')
            }
            
            logger.info(f"🔥 EXECUTING SSE BOOKING: {booking_args}")
            
            result = await self.call_tool("book_room", booking_args)
            
            if result.get("success") and result.get("booking_confirmed"):
                response = f"""✅ **BOOKING CONFIRMED!** 🎉

**Booking Details:**
- **Booking ID:** {result['booking_id']}
- **Room:** {result['room_number']} ({result['room_type']})
- **Dates:** {result['check_in_date']} to {result['check_out_date']}
- **Adults:** {adults}
- **Total Cost:** ₹{result['total_cost']:,}

✅ **Hotel room data has been updated in the CSV file!**

Your booking is confirmed and the room status has been changed to 'Booked'."""
                
                self.conversation_history[session_id].append({"role": "assistant", "content": response})
                return {
                    "response": response,
                    "booking_confirmed": True,
                    "booking_data": result,
                    "tools_used": ["book_room"]
                }
            else:
                error_response = f"❌ **Booking Failed:** {result.get('error', 'Unknown error')}"
                self.conversation_history[session_id].append({"role": "assistant", "content": error_response})
                return {"response": error_response}
                
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return {"response": "Error processing your booking. Please try again."}
    
    async def _handle_room_request(self, message: str, context: Dict, session_id: str) -> Dict[str, Any]:
        """Handle room availability requests"""
        try:
            # Call SSE tool for available rooms
            result = await self.call_tool("get_available_rooms", {})
            
            if result.get("success") and result.get("available_rooms"):
                rooms = result["available_rooms"][:6]  # Show first 6
                
                room_list = []
                for room in rooms:
                    price = float(room.get('Price', 0))
                    room_list.append(f"🏠 **Room {room['Room Number']}**: {room['Room Type']} - ₹{price:,.0f}/night")
                
                response = f"""🏨 **Available Rooms:**

{chr(10).join(room_list)}

To book a room, say: "I want to book Room [number] for [number] adults"
Example: "I want to book Room 102 for 2 adults" """
                
                self.conversation_history[session_id].append({"role": "assistant", "content": response})
                return {
                    "response": response,
                    "available_rooms": rooms,
                    "tools_used": ["get_available_rooms"]
                }
            else:
                error_response = "No rooms available or error getting room data."
                self.conversation_history[session_id].append({"role": "assistant", "content": error_response})
                return {"response": error_response}
                
        except Exception as e:
            logger.error(f"Room request error: {e}")
            return {"response": "Error getting room information. Please try again."}
    
    async def disconnect(self):
        """Disconnect from SSE server"""
        logger.info("🔌 Disconnected from SSE server")

# Alias for compatibility with existing code
HotelMCPClient = HotelSSEClient

# For testing
async def test_sse_client():
    client = HotelSSEClient()
    
    if await client.connect():
        # Test guest lookup
        context = {"guest_name": "Vihaan Sharma"}
        result1 = await client.chat("Hello, I'm Vihaan Sharma", context)
        print("Guest lookup:", result1)
        
        # Test booking
        if result1.get("guest_profile"):
            context["guest_profile"] = result1["guest_profile"]
            result2 = await client.chat("I want to book Room 102 for 2 adults", context)
            print("Booking result:", result2)
        
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_sse_client())

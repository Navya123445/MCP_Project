# staff_interface.py - ENHANCED WITH ROOM FREEING FUNCTIONALITY
import streamlit as st
import requests
import json
import time
import os
from datetime import datetime
import pandas as pd
import re

st.set_page_config(
    page_title="👨‍💼 Staff Dashboard",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sidebar width and chat font size
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    width: 300px !important;
}
[data-testid="stChatMessageContent"] p {
    font-size: 1.1rem !important;
}
[data-testid="stChatMessageContent"] {
    font-size: 1.1rem !important;
}
</style>
""", unsafe_allow_html=True)

# Simple staff client
class StaffClient:
    def __init__(self):
        self.base_url = "http://localhost:8003"
        self.connected = False
    
    def connect(self):
        """Connect to server"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.connected = True
                return True
            return False
        except:
            return False
    
    def call_tool(self, tool_name: str, arguments: dict):
        """Call MCP tools"""
        try:
            response = requests.post(
                f"{self.base_url}/sse",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {"error": "No result"})
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
        
        
class OllamaClient:
    def __init__(self, host="http://localhost:11434", model="llama3.2"):
        self.host = host
        self.model = model
        try:
            import ollama
            self.client = ollama.Client(host=host)
        except ImportError:
            print("Warning: ollama package not installed. Install with: pip install ollama")
            self.client = None
        except Exception as e:
            print(f"Warning: Could not connect to Ollama: {e}")
            self.client = None
    
    def generate_response(self, prompt, model=None):
        """Generate response using Ollama"""
        if not self.client:
            return "Error: Ollama client not available. Please install ollama package and ensure Ollama is running."
        
        try:
            response = self.client.generate(
                model=model or self.model,
                prompt=prompt,
                stream=False
            )
            return response['response']
        except Exception as e:
            return f"Error generating response: {str(e)}. Please ensure Ollama is running and the model is available."
    
    def chat(self, messages, model=None):
        """Chat with Ollama using message format"""
        if not self.client:
            return "Error: Ollama client not available. Please install ollama package and ensure Ollama is running."
        
        try:
            response = self.client.chat(
                model=model or self.model,
                messages=messages,
                stream=False
            )
            return response['message']['content']
        except Exception as e:
            return f"Error in chat: {str(e)}. Please ensure Ollama is running and the model is available."
    
    def is_available(self):
        """Check if Ollama is available"""
        return self.client is not None

class StaffInterface:
    def __init__(self):
        self.guest_sessions_file = "active_guest_sessions.json"
        self.ensure_files()
        
        # Initialize client
        if 'staff_client' not in st.session_state:
            st.session_state.staff_client = None
        if 'staff_connected' not in st.session_state:
            st.session_state.staff_connected = False
        
        # Initialize LLM client for personalized recommendations
        self.ollama_client = OllamaClient()
        
        # Initialize progressive booking state
        if 'progressive_booking' not in st.session_state:
            st.session_state.progressive_booking = {}
    
    def ensure_files(self):
        """Ensure required files exist"""
        if not os.path.exists(self.guest_sessions_file):
            with open(self.guest_sessions_file, 'w') as f:
                json.dump({}, f)
    
    def initialize_client(self):
        """Initialize client"""
        if not st.session_state.staff_connected:
            try:
                if st.session_state.staff_client is None:
                    st.session_state.staff_client = StaffClient()
                
                if st.session_state.staff_client.connect():
                    st.session_state.staff_connected = True
                    return True
                else:
                    return False
                    
            except Exception as e:
                print(f"Staff client error: {e}")
                return False
        return True
    
    def get_all_guests(self):
        """Get all guests from server"""
        try:
            response = requests.get("http://localhost:8001/guests/all", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting guests: {e}")
            return []
    
    def get_all_rooms(self):
        """Get all rooms from server"""
        try:
            response = requests.get("http://localhost:8002/rooms/available", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting rooms: {e}")
            return []
    
    def search_guest_by_name(self, first_name, last_name):
        """Search guest by name"""
        try:
            params = {"first_name": first_name, "last_name": last_name}
            response = requests.get("http://localhost:8001/guest/by-name", params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error searching guest: {e}")
            return None
    
    def search_guest_by_phone(self, phone_number):
        """Search guest by phone"""
        try:
            response = requests.get(f"http://localhost:8001/guest/by-phone/{phone_number}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error searching guest: {e}")
            return None
    
    def update_room_with_guest_info(self, room_number, guest_data, booking_details):
        """Update room CSV with complete guest information"""
        try:
            # Prepare complete room update data
            room_update_data = {
                "room_number": room_number,
                "availability": "Booked",
                "guest_name": f"{guest_data.get('first_name', 'Guest')} {guest_data.get('last_name', 'Name')}",
                "number_of_people": booking_details.get('number_of_adults', 1),
                "check_in_date": booking_details.get('check_in_date', ''),
                "check_out_date": booking_details.get('check_out_date', ''),
                "extra_facility": guest_data.get('special_requests', '') or guest_data.get('amenities_used', ''),
                "action": "book_complete"
            }
            
            # Try to update room with complete guest information
            response = requests.put(
                f"http://localhost:8002/rooms/{room_number}/update-guest-info",
                json=room_update_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Room {room_number} updated with complete guest information"
                }
            else:
                # Fallback: Try alternative update method
                fallback_response = requests.put(
                    f"http://localhost:8002/rooms/{room_number}/status",
                    json=room_update_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if fallback_response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Room {room_number} updated with guest information (fallback method)"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to update room {room_number} with guest information"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating room with guest info: {str(e)}"
            }
    
    def free_room(self, room_number):
        """Free up a room - change status from Booked to Available"""
        try:
            # Prepare data for room status update
            room_data = {
                "room_number": room_number,
                "availability": "Available",
                "guest_name": "",  # Clear guest name
                "number_of_people": "",  # Clear people count
                "check_in_date": "",  # Clear check-in date
                "check_out_date": "",
                "extra_facility": "",  # Clear extra facilities
                "action": "checkout"
            }
            
            # Try to update room status via booking server
            response = requests.put(
                f"http://localhost:8002/rooms/{room_number}/status",
                json=room_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message": f"Room {room_number} successfully freed and made available",
                    "room_data": result
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": f"Room {room_number} not found"
                }
            elif response.status_code == 400:
                return {
                    "success": False,
                    "message": f"Room {room_number} is already available or invalid request"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to free room {room_number}: HTTP {response.status_code}"
                }
                
        except requests.exceptions.ConnectionError:
            # Fallback: Try alternative approach via booking cancellation
            try:
                cancel_response = requests.delete(
                    f"http://localhost:8002/bookings/room/{room_number}",
                    timeout=10
                )
                
                if cancel_response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Room {room_number} booking cancelled and room freed"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Cannot connect to booking server to free room {room_number}"
                    }
            except:
                return {
                    "success": False,
                    "message": f"Cannot connect to booking server to free room {room_number}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error freeing room {room_number}: {str(e)}"
            }
    
    def debug_booking_data(self, room_num, guest_id, check_in, check_out, adults):
        """Debug function to check booking data before sending"""
        try:
            # Check if guest exists
            guest_response = requests.get(f"http://localhost:8001/guest/by-id/{guest_id}", timeout=5)
            guest_exists = guest_response.status_code == 200
            
            # Check if room exists in available rooms
            rooms_response = requests.get("http://localhost:8002/rooms/available", timeout=5)
            room_exists = False
            if rooms_response.status_code == 200:
                rooms = rooms_response.json()
                room_exists = any(str(room.get('Room Number')) == str(room_num) for room in rooms)
            
            # Check date validity
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
                dates_valid = check_in_date < check_out_date
            except:
                dates_valid = False
            
            debug_info = f"""🔍 **Booking Debug Information:**

**Guest Check:** {'✅' if guest_exists else '❌'} Guest {guest_id} {'exists' if guest_exists else 'NOT FOUND'}
**Room Check:** {'✅' if room_exists else '❌'} Room {room_num} {'available' if room_exists else 'NOT AVAILABLE'}
**Date Check:** {'✅' if dates_valid else '❌'} Dates {'valid' if dates_valid else 'INVALID'}
**Adults:** {adults} (should be > 0)

**Servers Status:**
• Guest Server (8001): {'✅' if guest_response.status_code == 200 else '❌'}
• Booking Server (8002): {'✅' if rooms_response.status_code == 200 else '❌'}"""
            
            return debug_info
            
        except Exception as e:
            return f"Debug error: {str(e)}"
    
    def generate_personalized_recommendations_with_llm(self, guest_profile, available_rooms):
        """Generate personalized recommendations using LLM based on guest profile"""
        try:
            # Check if Ollama client is available
            if not self.ollama_client or not self.ollama_client.is_available():
                return self.generate_fallback_recommendations(guest_profile, available_rooms)
            
            # Extract specific guest details for analysis
            guest_name = f"{guest_profile.get('first_name', 'Guest')} {guest_profile.get('last_name', 'Name')}"
            purpose = guest_profile.get('purpose_of_visit', 'Not specified')
            origin = guest_profile.get('place_of_origin', 'Not specified')
            profession = guest_profile.get('profession', 'Not specified')
            loyalty = guest_profile.get('loyalty_member', 'New')
            spending = guest_profile.get('total_bill', 0)
            previous_room = guest_profile.get('room_type', 'Not specified')
            amenities = guest_profile.get('amenities_used', 'Standard')
            activities = guest_profile.get('extra_activities_booked', 'None')
            requests = guest_profile.get('special_requests', 'None')
            feedback = guest_profile.get('Feedback and issues raised', guest_profile.get('feedback_and_issues', 'None'))
            stay_days = guest_profile.get('Stay_days_number', 'Not specified')
            
            # Prepare available rooms context
            rooms_context = "AVAILABLE ROOMS:\n"
            for i, room in enumerate(available_rooms[:5], 1):
                rooms_context += f"{i}. Room {room.get('Room Number')}: {room.get('Room Type')} - ₹{float(room.get('Price', 0)):,.0f}/night\n"
            
            # Create highly specific prompt for personalized recommendations
            prompt = f"""You are a luxury hotel concierge creating SPECIFIC, ACTIONABLE recommendations for {guest_name}.

GUEST ANALYSIS:
Name: {guest_name}
Purpose of Visit: {purpose}
Origin: {origin}  
Profession: {profession}
Loyalty Status: {loyalty} member
Previous Spending: ₹{spending:,}
Stay Duration: {stay_days} days
Previous Room: {previous_room}
Amenities Used: {amenities}
Previous Activities: {activities}
Special Requests: {requests}
Past Feedback: {feedback}

{rooms_context}

TASK: Based on THIS SPECIFIC GUEST'S profile, create:

1. **SPECIFIC ROOM RECOMMENDATIONS** (analyze their profession, origin, purpose)
2. **CONCRETE UPSELLING SUGGESTIONS** (actual services/activities/amenities)
3. **TARGETED TALKING POINTS** (how to present based on their background)

ANALYSIS REQUIREMENTS:
- If they're from a specific city/region, mention local cultural preferences
- If they have a specific profession, suggest relevant amenities/services
- If they're here for business/leisure/wedding, tailor recommendations accordingly
- If they spent ₹X previously, suggest appropriate price point services
- If they used specific amenities before, suggest related upgrades

OUTPUT FORMAT:
## 🏨 **Personalized Recommendations for {guest_name}**

### **PROFILE ANALYSIS:**
**Guest Type:** [Analyze: Business traveler/Leisure guest/Wedding party/etc.]
**Spending Pattern:** [Analyze: Budget-conscious/Premium/Luxury seeker]
**Cultural Background:** [Analyze based on origin: Local preferences/International guest needs]
**Professional Needs:** [Analyze based on profession: Business facilities/Relaxation/Entertainment]

### **ROOM RECOMMENDATIONS:**

**1. Room [Number] - [Type] (₹[Price]/night)**
**Why Perfect for {guest_name}:**
- [Specific reason based on their profession/origin/purpose]
- [Connection to their previous preferences/spending]
- [Cultural/professional consideration]

**Staff Script:** "Mr./Ms. [Last Name], given your [profession/purpose], this room offers [specific benefit]. Since you're from [origin], you'll appreciate [specific feature]."

### **TARGETED UPSELLING OPPORTUNITIES:**

**Based on {guest_name}'s Profile:**

**🎯 RECOMMENDED SERVICES:**
- **[Specific Service 1]** - ₹[Price] | Because: [Reason based on their profile]
- **[Specific Service 2]** - ₹[Price] | Because: [Reason based on their profession/origin]
- **[Specific Service 3]** - ₹[Price] | Because: [Reason based on their purpose/preferences]

**EXAMPLE SERVICES TO CONSIDER:**
- Spa treatments (if stressed professional)
- Business center access (if business traveler)
- Cultural tours (if international guest)
- Airport transfers (if from out of town)
- Room service packages (if busy professional)
- Celebration packages (if special occasion)
- Fitness/yoga sessions (if health-conscious)
- Local cuisine experiences (if food lover)

**🗣️ CONVERSATION STARTERS:**
- "Since you're a [profession] from [origin], I'd recommend..."
- "For your [purpose] visit, guests typically enjoy..."
- "Given your [loyalty status] status and previous ₹[spending] experience..."

**💡 CULTURAL CONSIDERATIONS:**
[Specific suggestions based on their place of origin]

**🎯 FOLLOW-UP ACTIONS:**
- Present [specific room] first with [specific talking point]
- Offer [specific service] as natural add-on
- Prepare [specific alternative] if they decline

Remember: Be SPECIFIC, not generic. Use actual guest data to create targeted recommendations."""

            # Get LLM response
            response = self.ollama_client.generate_response(prompt)
            
            if response and len(response.strip()) > 100:
                return response
            else:
                return self.generate_fallback_recommendations(guest_profile, available_rooms)
                
        except Exception as e:
            print(f"LLM recommendation error: {e}")
            return self.generate_fallback_recommendations(guest_profile, available_rooms)

    def generate_fallback_recommendations(self, guest_profile, available_rooms):
        """Fallback recommendations if LLM fails"""
        guest_name = f"{guest_profile.get('first_name', 'Guest')} {guest_profile.get('last_name', 'Name')}"
        loyalty = guest_profile.get('loyalty_member', 'New')
        spending = guest_profile.get('total_bill', 0)
        
        response = f"## 🏨 **Recommendations for {guest_name}**\n\n"
        
        for i, room in enumerate(available_rooms[:3], 1):
            room_type = room.get('Room Type', 'Standard')
            price = float(room.get('Price', 0))
            
            response += f"### **{i}. Room {room.get('Room Number')} - {room_type} (₹{price:,.0f}/night)**\n"
            response += f"**Why This Works:** Perfect for {loyalty} member with ₹{spending:,} spending history\n"
            response += f"**Staff Note:** Present as value-focused option for their profile\n\n"
        
        return response

    def generate_room_recommendations_for_staff(self, guest_profile):
        """Generate personalized room recommendations using LLM analysis"""
        try:
            # Get available rooms
            available_rooms = self.get_all_rooms()
            if not available_rooms:
                return "No available rooms to recommend."
            
            # Use LLM to generate personalized recommendations
            personalized_response = self.generate_personalized_recommendations_with_llm(
                guest_profile, 
                available_rooms
            )
            
            # Add footer with booking instructions
            footer = """

---

### 💡 **How to Use These Recommendations:**

**🗣️ Conversation Starters:**
- "Based on your profile, I have some perfect room options for you..."
- "Given your [profession/origin/purpose], these rooms would be ideal..."
- "As a [loyalty status] member, you deserve our best recommendations..."

**📈 Revenue Optimization Tips:**
- Lead with the guest's specific interests and background
- Reference their previous positive experiences
- Bundle services that match their spending patterns
- Use cultural references that resonate with their origin

**🎯 Next Steps:**
- Present top recommendation first with personalized talking points
- Be ready to explain why each room matches their specific needs
- Prepare backup options if they decline initial recommendations"""

            return personalized_response + footer
            
        except Exception as e:
            return f"Error generating personalized recommendations: {str(e)}"
    
    def extract_keywords_and_intent(self, message):
        """Extract keywords and determine intent from natural language"""
        message_lower = message.lower()
        
        # Keywords for different intents
        guest_keywords = ['guest', 'guests', 'customer', 'customers', 'visitor', 'visitors']
        room_keywords = ['room', 'rooms', 'accommodation', 'suite', 'deluxe', 'family']
        search_keywords = ['find', 'search', 'look', 'locate', 'show', 'display', 'get']
        list_keywords = ['all', 'list', 'show', 'display', 'view']
        booking_keywords = ['book', 'reserve', 'reservation', 'booking', 'make', 'create']
        checkout_keywords = ['checkout', 'free', 'release', 'empty', 'available', 'clear']
        debug_keywords = ['debug', 'test', 'check', 'verify', 'validate']
        
        # Extract numbers, names, dates, and phone numbers
        numbers = re.findall(r'\b\d+\b', message)
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', message)
        phone_patterns = re.findall(r'\b\d{10,}\b', message)
        
        # Extract names (capitalized words that aren't common words)
        common_words = {'room', 'guest', 'book', 'for', 'from', 'to', 'the', 'and', 'or', 'in', 'on', 'at', 'with', 'by'}
        words = message.split()
        potential_names = [word for word in words if word.istitle() and word.lower() not in common_words]
        
        return {
            'message_lower': message_lower,
            'guest_keywords': any(kw in message_lower for kw in guest_keywords),
            'room_keywords': any(kw in message_lower for kw in room_keywords),
            'search_keywords': any(kw in message_lower for kw in search_keywords),
            'list_keywords': any(kw in message_lower for kw in list_keywords),
            'booking_keywords': any(kw in message_lower for kw in booking_keywords),
            'checkout_keywords': any(kw in message_lower for kw in checkout_keywords),
            'debug_keywords': any(kw in message_lower for kw in debug_keywords),
            'numbers': numbers,
            'dates': dates,
            'phone_patterns': phone_patterns,
            'potential_names': potential_names
        }
    
    def handle_progressive_booking(self, message, intent):
        """Handle progressive booking with follow-up questions"""
        booking_state = st.session_state.progressive_booking
        
        # Initialize booking if not started
        if not booking_state:
            booking_state = {
                'step': 'start',
                'guest_id': None,
                'room_number': None,
                'check_in': None,
                'check_out': None,
                'adults': None
            }
            st.session_state.progressive_booking = booking_state
        
        # Extract any information from current message
        if intent['numbers']:
            for num in intent['numbers']:
                num_int = int(num)
                if booking_state['step'] == 'guest_id' and not booking_state['guest_id']:
                    booking_state['guest_id'] = num_int
                elif booking_state['step'] == 'room_number' and not booking_state['room_number']:
                    booking_state['room_number'] = num_int
                elif booking_state['step'] == 'adults' and not booking_state['adults']:
                    booking_state['adults'] = num_int
        
        if intent['dates']:
            if not booking_state['check_in']:
                booking_state['check_in'] = intent['dates'][0]
            elif not booking_state['check_out'] and len(intent['dates']) > 1:
                booking_state['check_out'] = intent['dates'][1]
            elif not booking_state['check_out']:
                booking_state['check_out'] = intent['dates'][0]
        
        # Check what information is still missing
        missing_info = []
        if not booking_state['guest_id']:
            missing_info.append('guest_id')
        if not booking_state['room_number']:
            missing_info.append('room_number')
        if not booking_state['check_in']:
            missing_info.append('check_in')
        if not booking_state['check_out']:
            missing_info.append('check_out')
        if not booking_state['adults']:
            missing_info.append('adults')
        
        # If all information is available, process the booking
        if not missing_info:
            try:
                # Get guest details
                guest_response = requests.get(f"http://localhost:8001/guest/by-id/{booking_state['guest_id']}", timeout=10)
                if guest_response.status_code != 200:
                    st.session_state.progressive_booking = {}
                    return f"❌ Guest ID {booking_state['guest_id']} not found. Please start booking again with a valid guest ID."
                
                guest_data = guest_response.json()
                
                # Prepare booking data
                booking_data = {
                    "guest_id": booking_state['guest_id'],
                    "room_number": booking_state['room_number'],
                    "check_in_date": booking_state['check_in'],
                    "check_out_date": booking_state['check_out'],
                    "number_of_adults": booking_state['adults'],
                    "purpose_of_visit": guest_data.get('purpose_of_visit', 'Business'),
                    "guest_name": f"{guest_data.get('first_name', 'Guest')} {guest_data.get('last_name', 'Name')}"
                }
                
                # Make booking
                booking_response = requests.post(
                    "http://localhost:8002/bookings/create",
                    json=booking_data,
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                
                if booking_response.status_code == 200:
                    result = booking_response.json()
                    
                    # NEW: Update room with complete guest information
                    room_update_result = self.update_room_with_guest_info(
                        booking_state['room_number'], 
                        guest_data, 
                        booking_data
                    )
                    
                    # Clear booking state
                    st.session_state.progressive_booking = {}
                    
                    response = f"""✅ **Booking Completed Successfully!**

**Final Details:**
🏠 Room: {booking_state['room_number']} ({result.get('room_type', 'Standard')})
👤 Guest: {guest_data.get('first_name')} {guest_data.get('last_name')} (ID: {booking_state['guest_id']})
📅 Dates: {booking_state['check_in']} to {booking_state['check_out']}
👥 Adults: {booking_state['adults']}
🆔 Booking ID: {result.get('booking_id', 'Generated')}
💰 Total Cost: ₹{result.get('total_cost', 0):,}

✅ Booking has been confirmed and saved to the system!"""
                    
                    # Add room update status
                    if room_update_result['success']:
                        response += f"\n✅ Room CSV updated with guest information"
                    else:
                        response += f"\n⚠️ Room booking successful but CSV update had issues: {room_update_result['message']}"
                    
                    return response
                else:
                    st.session_state.progressive_booking = {}
                    return f"❌ Booking failed: {booking_response.status_code}. Please try again or check room availability."
                    
            except Exception as e:
                st.session_state.progressive_booking = {}
                return f"❌ Error processing booking: {str(e)}. Please start again."
        
        # Ask for missing information
        if 'guest_id' in missing_info:
            booking_state['step'] = 'guest_id'
            return "📋 I'll help you book a room! First, please provide the **Guest ID** or tell me the guest's name so I can look them up."
        
        elif 'room_number' in missing_info:
            booking_state['step'] = 'room_number'
            # Show available rooms
            try:
                rooms = self.get_all_rooms()
                if rooms:
                    room_list = "\n".join([f"🏠 Room {room.get('Room Number')}: {room.get('Room Type')} - ₹{float(room.get('Price', 0)):,.0f}/night" for room in rooms[:8]])
                    return f"""Great! For Guest ID {booking_state['guest_id']}, here are available rooms:

{room_list}

Please tell me which **room number** you'd like to book."""
                else:
                    st.session_state.progressive_booking = {}
                    return "❌ No rooms are currently available. Please check back later."
            except:
                return "Please specify which **room number** you'd like to book."
        
        elif 'check_in' in missing_info:
            booking_state['step'] = 'check_in'
            return f"Perfect! Booking Room {booking_state['room_number']} for Guest ID {booking_state['guest_id']}. What's the **check-in date**? (Please use format: YYYY-MM-DD, like 2025-07-15)"
        
        elif 'check_out' in missing_info:
            booking_state['step'] = 'check_out'
            return f"Great! Check-in is set for {booking_state['check_in']}. What's the **check-out date**? (Please use format: YYYY-MM-DD, like 2025-07-17)"
        
        elif 'adults' in missing_info:
            booking_state['step'] = 'adults'
            return f"Almost done! How many **adults** will be staying? (Just the number, like 2)"
        
        return "I have all the information I need. Processing your booking..."
    
    def handle_staff_chat(self, message, context=None):
        """Handle staff chat commands using intelligent keyword matching"""
        
        # Extract keywords and intent
        intent = self.extract_keywords_and_intent(message)
        
        try:
            # Check if this is a progressive booking scenario
            if (intent['booking_keywords'] and 
                (not intent['numbers'] or len(intent['numbers']) < 2 or not intent['dates'])) or \
               st.session_state.progressive_booking:
                return self.handle_progressive_booking(message, intent)
            
            # Guest Management - Show all guests
            if (intent['guest_keywords'] and intent['list_keywords']) or \
               ('all guest' in intent['message_lower']) or \
               ('show guest' in intent['message_lower']):
                guests = self.get_all_guests()
                if guests:
                    response = f"👥 **All Guests ({len(guests)} total):**\n\n"
                    
                    for guest in guests[:15]:  # Show first 15
                        response += f"**{guest.get('id', 'N/A')}. {guest.get('first_name', 'Unknown')} {guest.get('last_name', 'Guest')}**\n"
                        response += f"📧 {guest.get('email', 'No email')} | 📱 {guest.get('phone_number', 'No phone')}\n"
                        response += f"🏨 {guest.get('loyalty_member', 'New')} | 💰 ₹{guest.get('total_bill', 0):,}\n\n"
                    
                    if len(guests) > 15:
                        response += f"... and {len(guests) - 15} more guests"
                    
                    return response
                else:
                    return "❌ No guests found"
            
            # Room Management - Show all rooms
            elif (intent['room_keywords'] and intent['list_keywords']) or \
                 ('all room' in intent['message_lower']) or \
                 ('show room' in intent['message_lower']) or \
                 ('available room' in intent['message_lower']):
                rooms = self.get_all_rooms()
                if rooms:
                    response = f"🏨 **Available Rooms ({len(rooms)} total):**\n\n"
                    
                    for room in rooms[:12]:
                        price = float(room.get('Price', 0))
                        response += f"🏠 **Room {room.get('Room Number', 'N/A')}**: {room.get('Room Type', 'Standard')} - ₹{price:,.0f}/night\n"
                    
                    if len(rooms) > 12:
                        response += f"... and {len(rooms) - 12} more rooms"
                    
                    return response
                else:
                    return "❌ No rooms found"
            
            # Room Checkout/Free
            elif intent['checkout_keywords'] and intent['room_keywords'] and intent['numbers']:
                room_number = int(intent['numbers'][0]) if intent['numbers'] else None
                
                if room_number:
                    result = self.free_room(room_number)
                    
                    if result["success"]:
                        return f"""✅ **Room Successfully Freed!**

🏠 **Room {room_number}** is now **Available**
📊 Status changed from **Booked** → **Available**
🔄 Available room count updated
✅ Hotel database updated successfully!

Room {room_number} is ready for new bookings."""
                    else:
                        return f"❌ **Failed to free room {room_number}:**\n\n{result['message']}"
                else:
                    return "Please specify which room number you want to checkout/free."
            
            # Guest Search by Name
            elif intent['search_keywords'] and intent['guest_keywords'] and intent['potential_names']:
                if len(intent['potential_names']) >= 2:
                    first_name = intent['potential_names'][0]
                    last_name = " ".join(intent['potential_names'][1:])
                    
                    guest = self.search_guest_by_name(first_name, last_name)
                    if guest:
                        return f"""✅ **Guest Found:**

👤 **{guest['first_name']} {guest['last_name']} (ID: {guest['id']})**

📧 Email: {guest.get('email', 'Not provided')}
📱 Phone: {guest.get('phone_number', 'Not provided')}
📍 From: {guest.get('place_of_origin', 'Not specified')}
🏨 Loyalty: {guest.get('loyalty_member', 'New')} Member
💰 Spending: ₹{guest.get('total_bill', 0):,}
💼 Profession: {guest.get('profession', 'Not specified')}"""
                    else:
                        return f"❌ No guest found: {first_name} {last_name}"
                else:
                    return "Please provide both first and last name for searching."
            
            # Guest Search by Phone
            elif intent['search_keywords'] and (intent['phone_patterns'] or 'phone' in intent['message_lower']):
                phone_number = intent['phone_patterns'][0] if intent['phone_patterns'] else None
                if not phone_number:
                    # Try to extract phone from different patterns
                    phone_match = re.search(r'phone\s*(\d+)', intent['message_lower'])
                    if phone_match:
                        phone_number = phone_match.group(1)
                
                if phone_number:
                    guest = self.search_guest_by_phone(phone_number)
                    if guest:
                        return f"""✅ **Guest Found by Phone:**

👤 **{guest['first_name']} {guest['last_name']} (ID: {guest['id']})**

📱 Phone: {guest.get('phone_number', 'Not provided')}
📧 Email: {guest.get('email', 'Not provided')}
🏨 Loyalty: {guest.get('loyalty_member', 'New')} Member
💰 Spending: ₹{guest.get('total_bill', 0):,}"""
                    else:
                        return f"❌ No guest found with phone: {phone_number}"
                else:
                    return "Please provide a phone number to search."
            
            # Guest Profile by ID
            elif intent['guest_keywords'] and intent['numbers'] and len(intent['numbers']) == 1:
                guest_id = int(intent['numbers'][0])
                
                if st.session_state.staff_client:
                    result = st.session_state.staff_client.call_tool(
                        "get_contextual_guest_profile", 
                        {"guest_id": guest_id}
                    )
                    
                    if result.get('success') and result.get('guest_profile'):
                        guest = result['guest_profile']
                        
                        response = f"""👤 **Complete Guest Profile (ID: {guest_id}):**

**Personal Info:**
📧 {guest.get('email', 'N/A')} | 📱 {guest.get('phone_number', 'N/A')}
📍 From: {guest.get('place_of_origin', 'N/A')} | 💼 {guest.get('profession', 'N/A')}

## 🔥 **Hotel History:**
**🗣️ Preferred Language:** {guest.get('preferred_language', 'Not specified')}
**🏨 Loyalty:** {guest.get('loyalty_member', 'New')} Member
**💰 Total Spending:** ₹{guest.get('total_bill', 0):,}
**🏠 Previous Room:** {guest.get('room_type', 'N/A')}
**🛎️ Amenities Used:** {guest.get('amenities_used', 'Standard')}
**🎭 Activities:** {guest.get('extra_activities_booked', 'None')}

## 🎯 **Preferences:**
**⭐ Special Requests:** {guest.get('special_requests', 'None')}
**💳 Payment:** {guest.get('payment_method', 'N/A')}
**💬 Feedback/Issues:** {guest.get('Feedback and issues raised', guest.get('feedback_and_issues', 'None'))}

---

{self.generate_room_recommendations_for_staff(guest)}"""
                        
                        return response
                    else:
                        return f"❌ Guest ID {guest_id} not found"
                else:
                    return "❌ Client not connected"
            
            # Debug Booking
            elif intent['debug_keywords'] and intent['booking_keywords'] and len(intent['numbers']) >= 2 and len(intent['dates']) >= 2:
                room_num = int(intent['numbers'][0])
                guest_id = int(intent['numbers'][1])
                check_in = intent['dates'][0]
                check_out = intent['dates'][1]
                adults = int(intent['numbers'][2]) if len(intent['numbers']) > 2 else 1
                
                return self.debug_booking_data(room_num, guest_id, check_in, check_out, adults)
            
            # Complete Room Booking (with all details)
            elif intent['booking_keywords'] and intent['room_keywords'] and len(intent['numbers']) >= 2 and len(intent['dates']) >= 2:
                room_num = int(intent['numbers'][0])
                guest_id = int(intent['numbers'][1])
                check_in = intent['dates'][0]
                check_out = intent['dates'][1]
                adults = int(intent['numbers'][2]) if len(intent['numbers']) > 2 else 2
                
                # Get guest details first for complete booking data
                try:
                    guest_response = requests.get(f"http://localhost:8001/guest/by-id/{guest_id}", timeout=10)
                    if guest_response.status_code != 200:
                        return f"❌ Guest ID {guest_id} not found. Please verify the guest exists."
                    
                    guest_data = guest_response.json()
                except Exception as e:
                    return f"❌ Error getting guest data: {str(e)}"
                
                # Prepare COMPLETE booking data with all required fields
                booking_data = {
                    "guest_id": guest_id,
                    "room_number": room_num,
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "number_of_adults": adults,
                    "purpose_of_visit": guest_data.get('purpose_of_visit', 'Business'),
                    "guest_name": f"{guest_data.get('first_name', 'Guest')} {guest_data.get('last_name', 'Name')}"
                }
                
                # Use direct booking server call
                try:
                    booking_response = requests.post(
                        "http://localhost:8002/bookings/create",
                        json=booking_data,
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    if booking_response.status_code == 200:
                        result = booking_response.json()
                        
                        # NEW: Update room with complete guest information
                        room_update_result = self.update_room_with_guest_info(
                            room_num, 
                            guest_data, 
                            booking_data
                        )
                        
                        response = f"""✅ **Booking Successful!**

**Details:**
🏠 Room: {room_num} ({result.get('room_type', 'Standard')})
👤 Guest: {guest_data.get('first_name')} {guest_data.get('last_name')} (ID: {guest_id})
📅 Dates: {check_in} to {check_out}
👥 Adults: {adults}
🆔 Booking ID: {result.get('booking_id', 'Generated')}
💰 Cost: ₹{result.get('total_cost', 0):,}

✅ Hotel database updated successfully!"""

                        # Add room update status
                        if room_update_result['success']:
                            response += f"\n✅ Room CSV updated with complete guest information"
                        else:
                            response += f"\n⚠️ Room booking successful but CSV update had issues: {room_update_result['message']}"
                        
                        return response
                    
                    elif booking_response.status_code == 400:
                        return f"❌ Booking failed: Room {room_num} may not be available or invalid data provided."
                    elif booking_response.status_code == 404:
                        return f"❌ Room {room_num} not found or not available."
                    elif booking_response.status_code == 409:
                        return f"❌ Room {room_num} is already booked for those dates."
                    else:
                        return f"❌ Booking failed: HTTP {booking_response.status_code}"
                        
                except requests.exceptions.Timeout:
                    return "❌ Booking timeout. Please try again."
                except requests.exceptions.ConnectionError:
                    return "❌ Cannot connect to booking server. Please check if it's running."
                except Exception as e:
                    return f"❌ Booking error: {str(e)}"
            
            # Help and default response
            else:
                return """👨‍💼 **How can I assist you?**

I can help you with:

🏨 **Guest Services:**
• Find and view guest profiles
• Search guests by name or phone
• View guest history and preferences

🏠 **Room Operations:**
• Show available rooms
• Book rooms with step-by-step guidance
• Free/checkout rooms

💬 **Natural Conversation:**
Just tell me what you need! For example:
• "Book a room" - I'll guide you through the process
• "Show available rooms"
• "Find guest John Smith"
• "Free room 122"
• "Guest 25" - View complete profile

What would you like to do?"""
        
        except Exception as e:
            return f"❌ Error processing your request: {str(e)}. Please try rephrasing your request."
    
    def load_active_sessions(self):
        """Load active guest sessions"""
        try:
            with open(self.guest_sessions_file, 'r') as f:
                sessions = json.load(f)
            
            # Filter recent sessions (last 2 hours)
            current_time = time.time()
            active_sessions = {
                sid: data for sid, data in sessions.items()
                if current_time - data.get('last_updated', 0) < 7200
            }
            
            return active_sessions
        except Exception as e:
            print(f"Error loading sessions: {e}")
            return {}
    
    def render_guest_monitor(self):
        """Real-time guest monitor"""
        st.subheader("👥 Active Guest Sessions")
        
        sessions = self.load_active_sessions()
        
        if not sessions:
            st.info("No active guest sessions")
            return
        
        st.success(f"🟢 **{len(sessions)} active guest(s)**")
        
        for session_id, session_data in sessions.items():
            guest_profile = session_data.get('guest_profile', {})
            guest_name = f"{guest_profile.get('first_name', 'Unknown')} {guest_profile.get('last_name', 'Guest')}"
            last_activity = session_data.get('last_updated', time.time())
            activity_time = datetime.fromtimestamp(last_activity).strftime("%H:%M:%S")
            
            with st.expander(f"👤 {guest_name} - Active since {activity_time}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {guest_profile.get('id', 'N/A')}")
                    st.write(f"**Email:** {guest_profile.get('email', 'N/A')}")
                    st.write(f"**Phone:** {guest_profile.get('phone_number', 'N/A')}")
                    st.write(f"**Loyalty:** {guest_profile.get('loyalty_member', 'New')}")
                
                with col2:
                    if st.button(f"👤 View Profile", key=f"profile_{session_id}"):
                        guest_id = guest_profile.get('id')
                        if guest_id:
                            st.session_state.quick_command = f"Guest {guest_id}"
                            st.session_state.staff_view = "chatbot"
                            st.rerun()
    
    def render_overview(self):
        """Guest/Room overview"""
        st.subheader("📊 System Overview")
        
        tab1, tab2 = st.tabs(["👥 Guest Overview", "🏨 Room Overview"])
        
        with tab1:
            # Search functionality
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔍 Search by Name:**")
                first_name = st.text_input("First Name", key="search_fname")
                last_name = st.text_input("Last Name", key="search_lname")
                if st.button("Search by Name"):
                    if first_name and last_name:
                        guest = self.search_guest_by_name(first_name, last_name)
                        if guest:
                            st.success(f"Found: {guest['first_name']} {guest['last_name']} (ID: {guest['id']})")
                            st.json(guest)
                        else:
                            st.error(f"No guest found: {first_name} {last_name}")
            
            with col2:
                st.markdown("**📱 Search by Phone:**")
                phone = st.text_input("Phone Number", key="search_phone")
                if st.button("Search by Phone"):
                    if phone:
                        guest = self.search_guest_by_phone(phone)
                        if guest:
                            st.success(f"Found: {guest['first_name']} {guest['last_name']} (ID: {guest['id']})")
                            st.json(guest)
                        else:
                            st.error(f"No guest found with phone: {phone}")
            
            # Load all guests
            if st.button("📋 Load All Guests"):
                guests = self.get_all_guests()
                if guests:
                    st.success(f"Loaded {len(guests)} guests")
                    df = pd.DataFrame(guests)
                    
                    display_columns = ['id', 'first_name', 'last_name', 'email', 'phone_number', 
                                     'loyalty_member', 'total_bill', 'place_of_origin', 'profession']
                    
                    available_columns = [col for col in display_columns if col in df.columns]
                    st.dataframe(df[available_columns], use_container_width=True, height=400)
                else:
                    st.error("No guests found")
        
        with tab2:
            if st.button("🏠 Load All Rooms"):
                rooms = self.get_all_rooms()
                if rooms:
                    st.success(f"Loaded {len(rooms)} rooms")
                    df = pd.DataFrame(rooms)
                    st.dataframe(df, use_container_width=True, height=400)
                else:
                    st.error("No rooms found")
    
    def render_chatbot(self):
        """Staff chatbot"""
        st.subheader("💬 Staff Assistant")
        
        # Initialize client
        if self.initialize_client():
            st.success("✅ Staff Assistant Ready")
        else:
            st.error("❌ Assistant Unavailable")
            return
        
        # Initialize chat
        if "staff_messages" not in st.session_state:
            st.session_state.staff_messages = [{
                "role": "assistant",
                "content": """👨‍💼 **Staff Assistant Ready!**

I'm here to help you with guest services and room operations. Just tell me what you need in natural language!

**Quick Examples:**
• *"Book a room"* - I'll guide you step by step
• *"Show available rooms"* 
• *"Find guest John Smith"*
• *"Free room 122"*
• *"Guest 25"* - View complete profile

Just type what you need - no specific commands required!"""
            }]
        
        # Handle quick commands from monitor
        if hasattr(st.session_state, 'quick_command'):
            quick_cmd = st.session_state.quick_command
            del st.session_state.quick_command
            
            st.session_state.staff_messages.append({"role": "user", "content": quick_cmd})
            
            with st.chat_message("user"):
                st.markdown(quick_cmd)
            
            with st.chat_message("assistant"):
                response = self.handle_staff_chat(quick_cmd)
                st.markdown(response)
                st.session_state.staff_messages.append({"role": "assistant", "content": response})
        
        # Display chat
        for message in st.session_state.staff_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Enter staff commands..."):
            st.session_state.staff_messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                response = self.handle_staff_chat(prompt)
                st.markdown(response)
                st.session_state.staff_messages.append({"role": "assistant", "content": response})
    
    def render_sidebar(self):
        """Sidebar navigation"""
        with st.sidebar:
            st.header("👨‍💼 Staff Dashboard")
            
            # System status
            try:
                guest_ok = requests.get("http://localhost:8001/", timeout=5).status_code == 200
                booking_ok = requests.get("http://localhost:8002/", timeout=5).status_code == 200
                mcp_ok = requests.get("http://localhost:8003/", timeout=5).status_code == 200
                
                if guest_ok and booking_ok and mcp_ok:
                    st.success("🟢 All systems operational")
                else:
                    st.error("🔴 System issues detected")
            except:
                st.error("🔴 Cannot connect to servers")
            
            # Navigation
            st.subheader("📱 Navigation")
            
            if st.button("👥 Guest Monitor"):
                st.session_state.staff_view = "monitor"
                st.rerun()
            
            if st.button("💬 Staff Assistant"):
                st.session_state.staff_view = "chatbot"
                st.rerun()
                
            if st.button("📊 Overview"):
                st.session_state.staff_view = "overview"
                st.rerun()
            
            # Stats
            st.divider()
            st.subheader("📊 Quick Stats")
            
            try:
                guests = self.get_all_guests()
                st.metric("Total Guests", len(guests))
            except:
                st.metric("Total Guests", "Error")
            
            try:
                rooms = self.get_all_rooms()
                st.metric("Available Rooms", len(rooms))
            except:
                st.metric("Available Rooms", "Error")
            
            sessions = self.load_active_sessions()
            st.metric("Active Sessions", len(sessions))
    
    def render_dashboard(self):
        """Main dashboard"""
        st.title("👨‍💼 Hotel Staff Dashboard")
        st.caption("Guest Management • Room Operations • Real-time Monitoring")
        
        # Route views
        view = st.session_state.get('staff_view', 'monitor')
        
        if view == 'monitor':
            self.render_guest_monitor()
        elif view == 'chatbot':
            self.render_chatbot()
        elif view == 'overview':
            self.render_overview()
        else:
            self.render_guest_monitor()

def main():
    interface = StaffInterface()
    interface.render_sidebar()
    interface.render_dashboard()

if __name__ == "__main__":
    main()

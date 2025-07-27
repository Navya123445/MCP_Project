# guest_interface.py - DYNAMIC LLM-POWERED HOTEL ASSISTANT - WITH BOOKING FUNCTIONALITY
import streamlit as st
import uuid
import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from dateutil.parser import parse as date_parse
import re


def init_session_state():
    """Initialize all session state variables immediately"""
    keys_to_init = {
        'session_id': str(uuid.uuid4()),
        'mcp_client': None,
        'client_connected': False,
        'mcp_messages': [{
            "role": "assistant",
            "content":'<div style="font-size:1.3rem; font-weight:600;">🤖 Welcome to your <b>AI Hotel Assistant</b>! I can show you available rooms, provide personalized recommendations, and answer any travel questions using my knowledge. Please identify yourself to get started!</div>'}],
        'guest_context': {},
        'profile_synced': False,
        'guest_identified': False,
        'current_guest_profile': None,
        'contextual_insights': None,
        'conversation_context': [],
        'show_room_table': False,
        'current_room_data': None,
        # NEW: Add booking state management
        'booking_dates_requested': False,
        'pending_check_in': None,
        'pending_check_out': None,
        'date_collection_step': None,
        'last_search_dates': None,
        'progressive_booking': {}
    }
    
    for key, default_value in keys_to_init.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


init_session_state()


st.set_page_config(
    page_title="🧠 AI Hotel Assistant",
    page_icon="🤖",
    layout="wide"
)


class OllamaClient:
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model_name = "phi4-mini:3.8b"
        self.available = self.check_availability()
    
    def check_availability(self):
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(self.model_name in model.get("name", "") for model in models)
            return False
        except:
            return False
    
    def generate_response(self, prompt, system_message="You are a helpful hotel concierge assistant with extensive knowledge about travel, hotels, and local recommendations."):
        """Generate response using Phi-4-mini via Ollama"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 300  # Increased for recommendations
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=600
            )
            
            if response.status_code == 200:
                return response.json()["message"]["content"]
            else:
                return "I'm having trouble generating a response right now. Please try again."
                
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try again."


class ContextAwareSSEClient:
    def __init__(self):
        self.base_url = "http://localhost:8003"
        self.connected = False
    
    def connect(self):
        """Connect to context-aware SSE server"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("message") == "Context-Aware Hotel MCP Server":
                    self.connected = True
                    return True
            return False
        except:
            return False
    
    def call_context_tool(self, tool_name: str, arguments: dict):
        """Call context-aware MCP tools"""
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


class IntelligentHotelAgent:
    def __init__(self):
        self.mcp_client = None
        self.ollama_client = OllamaClient()
    
    def get_mcp_client(self):
        """Get or create MCP client"""
        if st.session_state['mcp_client'] is None:
            st.session_state['mcp_client'] = ContextAwareSSEClient()
        return st.session_state['mcp_client']
    
    def initialize_connection(self):
        """Initialize MCP connection"""
        if st.session_state['client_connected']:
            return True
        
        with st.spinner("🧠 Connecting to Hotel Server..."):
            try:
                client = self.get_mcp_client()
                if client.connect():
                    st.session_state['client_connected'] = True
                    st.success("✅ AI Hotel Assistant Connected!")
                    return True
                else:
                    st.error("❌ Failed to connect to hotel server")
                    return False
            except Exception as e:
                st.error(f"❌ Connection error: {e}")
                return False
    
    def get_all_rooms(self, check_in_date=None, check_out_date=None):
        """Get all rooms from server with optional date filtering"""
        try:
            # Use the correct endpoint for guest interface with date filtering
            if check_in_date and check_out_date:
                # Use the date-filtered endpoint that excludes reserved rooms
                response = requests.get(
                    f"http://localhost:8002/rooms/available-for-dates",
                    params={"check_in": check_in_date, "check_out": check_out_date},
                    timeout=10
                )
            else:
                # Use the regular endpoint that excludes reserved rooms
                response = requests.get("http://localhost:8002/rooms/available", timeout=10)
            
            if response.status_code == 200:
                rooms = response.json()
                return rooms
            return []
        except Exception as e:
            print(f"Error getting rooms: {e}")
            return []
    
    def filter_rooms_by_dates(self, df, check_in_date, check_out_date):
        """Filter rooms based on date availability"""
        from datetime import datetime
        
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
            
            # Filter available rooms
            available_rooms = []
            
            for idx, room in df.iterrows():
                room_available = False
                
                # If room is currently Available, it's good to go
                if room['Availability'] == 'Available':
                    room_available = True
                
                # If room is Booked, check if it will be free during requested period
                elif room['Availability'] == 'Booked':
                    room_checkout = room.get('Check-out Date', '')
                    if room_checkout:
                        try:
                            checkout_date = datetime.strptime(room_checkout, '%Y-%m-%d')
                            # Room will be available if its checkout is before or on our checkin
                            if checkout_date <= check_in:
                                room_available = True
                        except:
                            pass  # Invalid date format, skip this room
                
                if room_available:
                    available_rooms.append(idx)
            
            return df.loc[available_rooms]
            
        except Exception as e:
            print(f"Date filtering error: {e}")
            return df  # Return unfiltered if error
    
    def extract_dates_from_message(self, message):
        """Extract dates from user message"""
        import re
        from datetime import datetime, timedelta
        
        def parse_flexible_date(date_str):
            try:
                parsed_date = date_parse(date_str, dayfirst=False)
                return parsed_date.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        
        extracted_dates = []
        if " to " in message:
            date_parts = message.split(" to ")
            if len(date_parts) == 2:
                date1 = parse_flexible_date(date_parts[0].strip())
                date2 = parse_flexible_date(date_parts[1].strip())
                if date1 and date2:
                    extracted_dates.extend([date1, date2])
                    
        elif "check-in" in message.lower() and "check-out" in message.lower():
            pattern = r'check-in:\s*([^,]+).*check-out:\s*(.+)'
            match = re.search(pattern, message.lower())
            if match:
                date1 = parse_flexible_date(match.group(1).strip())
                date2 = parse_flexible_date(match.group(2).strip())
                if date1 and date2:
                    extracted_dates.extend([date1, date2])  
        else:
            
            # Look for date patterns
            date_patterns = [
                r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY or DD/MM/YYYY
                r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # MM-DD-YYYY or DD-MM-YYYY
                r'\b\w+ \d{1,2}, \d{4}\b',  # Month DD, YYYY
                r'\b\d{1,2} \w+ \d{4}\b',  # DD Month YYYY
                
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, message)
                for match in matches:
                    parsed = parse_flexible_date(match)
                    if parsed:
                        extracted_dates.append(parsed)
            

        # Look for relative dates
        today = datetime.now()
        relative_dates = []
        
        if 'today' in message.lower():
            relative_dates.append(today.strftime('%Y-%m-%d'))
        if 'tomorrow' in message.lower():
            relative_dates.append((today + timedelta(days=1)).strftime('%Y-%m-%d'))
        if 'next week' in message.lower():
            relative_dates.append((today + timedelta(days=7)).strftime('%Y-%m-%d'))
        
        # Combine all found dates
        all_dates = extracted_dates + relative_dates
        
        return all_dates[:2]  # Return max 2 dates
    
    def extract_keywords_and_intent(self, message):
        """Extract keywords and determine intent from natural language"""
        message_lower = message.lower()
        
        # Keywords for different intents
        room_keywords = ['room', 'rooms', 'accommodation', 'suite', 'deluxe', 'family']
        booking_keywords = ['book', 'reserve', 'reservation', 'booking', 'make', 'create']
        
        # Extract numbers, names, dates
        numbers = re.findall(r'\b\d+\b', message)
        dates = self.extract_dates_from_message(message)
        
        return {
            'message_lower': message_lower,
            'room_keywords': any(kw in message_lower for kw in room_keywords),
            'booking_keywords': any(kw in message_lower for kw in booking_keywords),
            'numbers': numbers,
            'dates': dates
        }
    
    def handle_progressive_booking(self, message, intent):
        """Handle progressive booking with follow-up questions - GUEST VERSION"""
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
        
        if (not booking_state.get('check_in') and not booking_state.get('check_out') and 
        st.session_state.get('last_search_dates')):
            last_dates = st.session_state['last_search_dates']
            # Use dates if they were collected recently (within last 30 minutes)
            search_time = datetime.fromisoformat(last_dates['search_timestamp'])
            if (datetime.now() - search_time).total_seconds() < 1800:  # 30 minutes
                booking_state['check_in'] = last_dates['check_in']
                booking_state['check_out'] = last_dates['check_out']
                print(f"DEBUG: Reusing dates from room search: {booking_state['check_in']} to {booking_state['check_out']}")
                         
        
        # Get guest ID from current profile
        if st.session_state.get('current_guest_profile') and not booking_state.get('guest_id'):
            booking_state['guest_id'] = st.session_state['current_guest_profile'].get('id')
        
        # Extract any information from current message
        if intent['numbers']:
            for num in intent['numbers']:
                num_int = int(num)
                if booking_state['step'] == 'room_number' and not booking_state['room_number']:
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
            return self.process_guest_booking(booking_state)
        
        # Ask for missing information
        if 'guest_id' in missing_info:
            return "📋 To book a room, please first load your guest profile using the sidebar. I need your profile information to complete the booking."
        
        elif 'room_number' in missing_info:
            booking_state['step'] = 'room_number'
            # Show available rooms for the dates if we have them
            if booking_state['check_in'] and booking_state['check_out']:
                try:
                    rooms = self.get_all_rooms(booking_state['check_in'], booking_state['check_out'])
                    if rooms:
                        room_list = "\n".join([f"🏠 Room {room.get('Room Number')}: {room.get('Room Type')} - ₹{float(room.get('Price', 0)):,.0f}/night" for room in rooms[:8]])
                        return f"""Great! For your dates ({booking_state['check_in']} to {booking_state['check_out']}), here are available rooms:

{room_list}

Please tell me which **room number** you'd like to book."""
                    else:
                        st.session_state.progressive_booking = {}
                        return "❌ No rooms are available for your selected dates. Please try different dates."
                except:
                    return "Please specify which **room number** you'd like to book."
            else:
                return "Please specify which **room number** you'd like to book."
        
        elif 'check_in' in missing_info:
            booking_state['step'] = 'check_in'
            return f"Perfect! I'll book Room {booking_state['room_number']} for you. What's your **check-in date**? (Please use format: YYYY-MM-DD, like 2025-07-15)"
        
        elif 'check_out' in missing_info:
            booking_state['step'] = 'check_out'
            return f"Great! Check-in is set for {booking_state['check_in']}. What's your **check-out date**? (Please use format: YYYY-MM-DD, like 2025-07-17)"
        
        elif 'adults' in missing_info:
            booking_state['step'] = 'adults'
            return f"Almost done! How many **adults** will be staying? (Just the number, like 2)"
        
        return "I have all the information I need. Processing your booking..."
    
    def process_guest_booking(self, booking_state):
        """Process the actual booking for guest"""
        try:
            guest_profile = st.session_state.get('current_guest_profile')
            if not guest_profile:
                st.session_state.progressive_booking = {}
                return "❌ Guest profile not found. Please load your profile first."
            
            required_fields = ['guest_id', 'room_number', 'check_in', 'check_out', 'adults']
            missing_fields = [field for field in required_fields if not booking_state.get(field)]
            
            if missing_fields:
                return f"❌ Missing required information: {', '.join(missing_fields)}"
            
            # Prepare booking data
            booking_data = {
                "guest_id": booking_state['guest_id'],
                "room_number": booking_state['room_number'],
                "check_in_date": booking_state['check_in'],
                "check_out_date": booking_state['check_out'],
                "number_of_adults": booking_state['adults'],
                "purpose_of_visit": guest_profile.get('purpose_of_visit', 'Leisure'),
                "guest_name": f"{guest_profile.get('first_name', 'Guest')} {guest_profile.get('last_name', 'Name')}"
            }
            
            # Make booking request
            booking_response = requests.post(
                "http://localhost:8002/bookings/create",
                json=booking_data,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if booking_response.status_code == 200:
                result = booking_response.json()
                
                # Update room with guest information
                room_update_success=self.update_room_with_guest_info(
                    booking_state['room_number'], 
                    guest_profile, 
                    booking_data
                )
                
                # Clear booking state
                st.session_state.progressive_booking = {}
                # Clear room table to prevent interference
                st.session_state['show_room_table'] = False
                st.session_state['current_room_data'] = None
                
                
                booking_response_text = f"""✅ **Booking Confirmed Successfully!**

**Your Booking Details:**
🏠 Room: {booking_state['room_number']} ({result.get('room_type', 'Standard')})
👤 Guest: {guest_profile.get('first_name')} {guest_profile.get('last_name')}
📅 Dates: {booking_state['check_in']} to {booking_state['check_out']}
👥 Adults: {booking_state['adults']}
🆔 Booking ID: {result.get('booking_id', 'Generated')}
💰 Total Cost: ₹{result.get('total_cost', 0):,}

🎉 **Your room is now reserved!** You'll receive a confirmation email shortly.
📞 For any changes, please contact our staff.

Thank you for choosing Hotel Inn! 🏨"""
                # Add room update status
                if room_update_success:
                    booking_response_text += f"\n\n✅ Room database updated successfully!"
                return booking_response_text
                    
            elif booking_response.status_code == 400:
                st.session_state.progressive_booking = {}
                return f"❌ **Booking failed:** Room {booking_state['room_number']} may not be available for the selected dates. Please choose different dates or room."
                
            elif booking_response.status_code == 404:
                st.session_state.progressive_booking = {}
                return f"❌ **Booking failed:** Room {booking_state['room_number']} not found. Please select a different room."
            
            elif booking_response.status_code == 409:
                st.session_state.progressive_booking = {}
                return f"❌ **Booking failed:** Room {booking_state['room_number']} is already booked for those dates. Please choose different dates."
            
        
            else:
                st.session_state.progressive_booking = {}
                return f"❌ Booking failed. Please try again or contact our staff for assistance."
        
        except requests.exceptions.Timeout:
            st.session_state.progressive_booking = {}
            return "❌ **Booking timeout:** Please try again. If the problem persists, contact our staff."        
        
        except requests.exceptions.ConnectionError:
            st.session_state.progressive_booking = {}
            return "❌ **Connection error:** Cannot connect to booking server. Please contact our staff."
        
        except Exception as e:
            st.session_state.progressive_booking = {}
            return f"❌ Error processing booking: {str(e)}. Please try again or contact our staff."
        
        
    
    def update_room_with_guest_info(self, room_number, guest_data, booking_details):
        """Update room with complete guest information"""
        try:
            # Prepare room update data
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
            
            print(f"DEBUG: Room update data: {room_update_data}")
            response = requests.put(
                f"http://localhost:8002/rooms/{room_number}/update-guest-info",
                json=room_update_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"DEBUG: Room {room_number} updated successfully")
                return True
            else:  
                # Fallback: Try alternative update method
                fallback_response = requests.put(
                f"http://localhost:8002/rooms/{room_number}/status",
                json=room_update_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            ) 
                 
        except Exception as e:
            print(f"Error updating room: {e}")
            return False
    
    def generate_guest_recommendations(self, guest_profile):
        """Generate room recommendations matching staff interface logic"""
        try:
            # Get available rooms
            available_rooms = self.get_all_rooms()
            if not available_rooms:
                return "No available rooms to recommend."
            
            # Extract guest preferences (same logic as staff interface)
            loyalty = guest_profile.get('loyalty_member', 'New')
            previous_room = guest_profile.get('room_type', '').lower()
            spending = guest_profile.get('total_bill', 0)
            special_requests = guest_profile.get('special_requests', '').lower()
            amenities_used = guest_profile.get('amenities_used', '').lower()
            purpose = guest_profile.get('purpose_of_visit', '').lower()
            origin = guest_profile.get('place_of_origin', '')
            
            recommendations = []
            
            # Analyze available rooms and create recommendations (same logic as staff interface)
            for room in available_rooms[:5]:  # Top 5 recommendations
                room_type = room.get('Room Type', '').lower()
                room_number = room.get('Room Number')
                price = float(room.get('Price', 0))
                
                # Generate recommendation based on guest profile
                guest_benefits = []
                
                # Previous preference matching
                if previous_room and room_type == previous_room:
                    guest_benefits.append(f"Perfect match for your previous {previous_room} room experience")
                
                # Loyalty-based recommendations
                if loyalty in ['Silver', 'Gold'] and room_type in ['suite', 'deluxe']:
                    guest_benefits.append(f"VIP treatment for our {loyalty} member with premium {room_type}")
                
                # Spending pattern analysis
                if spending > 8000 and price > 5000:
                    guest_benefits.append(f"Aligns with your preference for premium experiences")
                elif spending < 5000 and price < 4000:
                    guest_benefits.append(f"Great value while maintaining quality")
                
                # Special requests accommodation
                if 'extra bed' in special_requests and room_type in ['family', 'suite']:
                    guest_benefits.append(f"{room_type.title()} room can easily accommodate extra bedding")
                
                if 'medicine' in special_requests:
                    guest_benefits.append(f"Convenient location close to front desk for easy assistance")
                
                # Amenities matching
                if 'spa' in amenities_used and room_type in ['deluxe', 'suite']:
                    guest_benefits.append(f"Premium rooms include enhanced spa service access")
                
                if 'gym' in amenities_used:
                    guest_benefits.append(f"Convenient location near fitness facilities")
                
                # Purpose-based recommendations
                if 'business' in purpose and room_type in ['deluxe', 'suite']:
                    guest_benefits.append(f"Spacious workspace and quiet environment for meetings")
                
                if 'wedding' in purpose and room_type == 'suite':
                    guest_benefits.append(f"Elegant suite ideal for special occasions")
                
                # Cultural considerations
                if origin and room_type == 'family':
                    guest_benefits.append(f"Spacious accommodation perfect for {origin} family traditions")
                
                # Add default benefits if none matched
                if not guest_benefits:
                    if room_type == 'suite':
                        guest_benefits.append("Our finest accommodation with premium amenities")
                    elif room_type == 'deluxe':
                        guest_benefits.append("Enhanced comfort with upgraded amenities and superior location")
                    elif room_type == 'family':
                        guest_benefits.append("Spacious living perfect for relaxation and comfort")
                    else:
                        guest_benefits.append("Quality accommodation with all essential amenities")
                
                recommendations.append({
                    'room_number': room_number,
                    'room_type': room_type.title(),
                    'price': price,
                    'benefits': guest_benefits[:3]  # Limit to top 3 benefits
                })
            
            # Format recommendations for guest display
            response = f"## 🏨 **Personalized Room Recommendations for {guest_profile.get('first_name')}:**\n\n"
            response += f"*Based on your previous **{guest_profile.get('room_type', 'room')}** stay and **{guest_profile.get('purpose_of_visit', 'visit')}** purpose*\n\n"
            
            for i, rec in enumerate(recommendations[:3], 1):
                response += f"### **{i}. Room {rec['room_number']} - {rec['room_type']} (₹{rec['price']:,.0f}/night)**\n\n"
                response += "**Why this room is perfect for you:**\n"
                for benefit in rec['benefits']:
                    response += f"• {benefit}\n"
                response += f"\n💬 **To book this room, just say:** *\"Book room {rec['room_number']}\"*\n\n"
            
            # Add upselling opportunities based on guest profile
            response += "### 🎯 **Additional Services We Recommend:**\n\n"
            
            # Personalized upselling based on profile
            if purpose == 'business':
                response += "**🏢 Business Services:**\n"
                response += "• Meeting room facilities for your business needs\n"
                response += "• Business center with printing and internet services\n"
                response += "• Executive lounge access for networking\n\n"
            
            if purpose == 'wedding':
                response += "**💒 Wedding Services:**\n"
                response += "• Special decoration arrangements for your celebration\n"
                response += "• Photography services to capture your moments\n"
                response += "• Catering arrangements for intimate gatherings\n\n"
            
            # Standard upselling for all guests
            response += "**🛎️ Premium Services:**\n"
            response += "• Airport pickup in luxury vehicles\n"
            response += "• Spa treatments for relaxation after your journey\n"
            response += "• 24/7 room service for your convenience\n\n"
            
            response += "**🍽️ Dining Experiences:**\n"
            if origin:
                response += f"• Special {origin} cuisine prepared by our chef\n"
            response += "• Multi-cuisine restaurant with local and international dishes\n"
            response += "• In-room dining for private meals\n\n"
            
            return response
            
        except Exception as e:
            return f"Error generating recommendations: {str(e)}"
    
    def intelligent_handler(self, message: str, context: dict = None):
        """ENHANCED: Main intelligent handler with booking functionality"""
        try:
            mcp_client = self.get_mcp_client()
            if not mcp_client.connected:
                return {"response": "Please connect to the hotel server first."}
            
            # Add to conversation context
            st.session_state['conversation_context'].append({
                "user_message": message,
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            })
            
            # NEW: Handle date collection for pending room requests
            if st.session_state.get('date_collection_step'):
                dates = self.extract_dates_from_message(message)
                # Debug: Print extracted dates
                print(f"DEBUG: Date collection step: {st.session_state['date_collection_step']}")
                print(f"DEBUG: Extracted dates from '{message}': {dates}")
                
                
                if st.session_state['date_collection_step'] == 'check_in':
                    if dates:
                        st.session_state['pending_check_in'] = dates[0]
                        st.session_state['date_collection_step'] = 'check_out'
                        return {"response": f"✅ Check-in date recorded: **{dates[0]}**\n\nNow please provide your **check-out date** in any format:\n\n**Examples:** July 18, 2025-07-18, 18/07/2025, tomorrow, etc."}
                    else:
                        return {"response": "❌ I couldn't understand that date format. Please try again with formats like:\n• July 15, 2025\n• 2025-07-15\n• 15/07/2025\n• tomorrow\n• today"}
            
                elif st.session_state['date_collection_step'] == 'check_out':
                    if dates:
                        st.session_state['pending_check_out'] = dates[0]
                        check_in = st.session_state['pending_check_in']
                        check_out = dates[0]
                    
                    # Clear date collection state
                        st.session_state['date_collection_step'] = None
                    # Now process the room availability with both dates
                        return self.handle_room_availability(f"Show available rooms from {check_in} to {check_out}", context)
                    else:
                        return {"response": "❌ I couldn't understand that date format. Please try again with formats like:\n• July 18, 2025\n• 2025-07-18\n• 18/07/2025\n• tomorrow\n• next week"}
                
            elif st.session_state.get('date_collection_step') and not any(word in message.lower() for word in ['date', '2025', '2024', 'check-in', 'check-out', 'july', 'august', 'september', 'october', 'november', 'december', 'january', 'february', 'march', 'april', 'may', 'june', 'today', 'tomorrow']):
                st.session_state['date_collection_step'] = None
                st.session_state['pending_check_in'] = None
                st.session_state['pending_check_out'] = None    
                
            # Extract keywords and intent
            intent = self.extract_keywords_and_intent(message)
            
            # ENHANCED ROUTING WITH BOOKING FUNCTIONALITY
            
            # 1. BOOKING FUNCTIONALITY - TOP PRIORITY
            if (intent['booking_keywords'] and 
                (not intent['numbers'] or len(intent['numbers']) < 2 or not intent['dates'])) or \
               st.session_state.progressive_booking:
                print(f"DEBUG: Routing to progressive booking for: {message}")
                return {"response": self.handle_progressive_booking(message, intent)}
            
            # 2. PERSONALIZED RECOMMENDATIONS - SECOND PRIORITY
            elif any(word in message.lower() for word in ['recommend', 'recommendation', 'suggest', 'which room', 'best room', 'previous stay', 'based on my']):
                print(f"DEBUG: Routing to personalized recommendations for: {message}")
                return self.handle_personalized_recommendations(message, context)
            
            # 3. ROOM AVAILABILITY - THIRD PRIORITY
            elif any(word in message.lower() for word in ['available rooms', 'show rooms', 'room availability', 'what rooms']):
                print(f"DEBUG: Routing to room availability for: {message}")
                return self.handle_room_availability(message, context)
            
            
            # 4. NEW: STANDALONE DATE INPUT - Handle dates like "July 20"
            elif (len(message.split()) <= 4 and 
              any(word in message.lower() for word in ['july', 'august', 'september', 'october', 'november', 'december', 'january', 'february', 'march', 'april', 'may', 'june', 'today', 'tomorrow', 'next']) and
              not any(word in message.lower() for word in ['recommend', 'book', 'available', 'show'])):
                print(f"DEBUG: Detected standalone date input: {message}")
            
                # If we're in date collection mode, handle it
                if st.session_state.get('date_collection_step'):
                    dates = self.extract_dates_from_message(message)
                
                    if st.session_state['date_collection_step'] == 'check_in' and dates:
                        st.session_state['pending_check_in'] = dates[0]
                        st.session_state['date_collection_step'] = 'check_out'
                        return {"response": f"✅ Check-in date recorded: **{dates[0]}**\n\nNow please provide your **check-out date**:"}
                
                    elif st.session_state['date_collection_step'] == 'check_out' and dates:
                        st.session_state['pending_check_out'] = dates[0]
                        check_in = st.session_state['pending_check_in']
                        check_out = dates[0]
                        st.session_state['date_collection_step'] = None
                        return self.handle_room_availability(f"Show available rooms from {check_in} to {check_out}", context)
            
                # If not in date collection mode, treat as general question
                else:
                    return self.handle_llm_powered_questions(message, context)
            
            # 5. GUEST PROFILE IDENTIFICATION - ONLY FOR PROFILE LOADING
            elif context and (context.get('guest_name') or context.get('guest_id')) and 'load my profile' in message.lower():
                print(f"DEBUG: Routing to profile lookup for: {message}")
                return self.handle_guest_profile_lookup(message, context)
            
            # 6. ALL OTHER QUESTIONS - Use Phi-4-mini's knowledge
            else:
                print(f"DEBUG: Routing to LLM for: {message}")
                return self.handle_llm_powered_questions(message, context)
                
        except Exception as e:
            return {"response": f"I encountered an error: {str(e)}. Please try asking something else."}
    
    def handle_personalized_recommendations(self, message: str, context: Dict):
        """NEW: Handle personalized ROOM recommendations matching staff interface"""
        try:
            guest_profile = context.get('guest_profile') if context else None
            
            if not guest_profile:
                return {"response": "I'd love to provide personalized room recommendations! Please load your guest profile first using the sidebar so I can analyze your previous stay and preferences."}
            
            # Use the same recommendation logic as staff interface
            recommendations = self.generate_guest_recommendations(guest_profile)
            
            return {"response": recommendations}
            
        except Exception as e:
            return {"response": f"I encountered an error generating room recommendations: {str(e)}. Please try again."}
    
    def handle_guest_profile_lookup(self, message: str, context: Dict):
        """Handle guest profile lookup with personalized touch"""
        try:
            mcp_client = self.get_mcp_client()
            
            # Prepare arguments
            if context.get('guest_id'):
                args = {"guest_id": context['guest_id']}
            elif context.get('guest_name'):
                name_parts = context['guest_name'].split()
                args = {"first_name": name_parts[0], "last_name": " ".join(name_parts[1:])}
            elif context.get('phone_number'):
                args={"phone_number": context['phone_number']}
            else:
                return {"response": "Please provide your guest ID or full name."}
            
            # Call contextual profile tool
            result = mcp_client.call_context_tool("get_contextual_guest_profile", args)
            
            if result.get("success") and result.get("guest_profile"):
                guest = result["guest_profile"]
                contextual_insights = guest.get("contextual_insights", {})
                
                # Sync with staff
                self.sync_with_staff(guest)
                
                # Format profile response - ENHANCED WITH RECOMMENDATION OPTIONS
                response = self.format_simple_profile_response(guest, contextual_insights)
                
                # Store contextual insights
                st.session_state['contextual_insights'] = contextual_insights
                
                return {
                    "response": response,
                    "guest_profile": guest,
                    "contextual_insights": contextual_insights
                }
            else:
                return {"response": "I couldn't find your profile. Please check your information."}
                
        except Exception as e:
            return {"response": f"Error loading profile: {str(e)}"}
    
    def format_simple_profile_response(self, guest, contextual_insights):
        """ENHANCED: Format profile with recommendation options"""
        
        response = f"""# 🎉 Welcome back, {guest['first_name']} {guest['last_name']}!


## 📊 Your Profile Summary


**🏨 Guest Details:**
- **Guest ID:** {guest['id']}
- **Loyalty Status:** {guest.get('loyalty_member', 'New')} Member  
- **From:** {guest.get('place_of_origin', 'Not specified')}
- **Profession:** {guest.get('profession', 'Not specified')}


**💰 Your Journey With Us:**
- **Total Spending:** ₹{guest.get('total_bill', 0):,}
- **Previous Room:** {guest.get('room_type', 'First visit')}
- **Purpose of Visit:** {guest.get('purpose_of_visit', 'Not specified')}
- **Payment Preference:** {guest.get('payment_method', 'Not specified')}


**🎯 Your Preferences:**
- **Amenities Used:** {guest.get('amenities_used', 'Standard')}
- **Activities Booked:** {guest.get('extra_activities_booked', 'None')}
- **Special Requests:** {guest.get('special_requests', 'None')}


---


## 💬 What Can I Help You With?


**🏨 Ask me:** "Show available rooms" - See all current options  
**🎯 Ask me:** "Recommend me a room" - Get personalized suggestions based on your profile  
**📅 Ask me:** "Book a room" - I'll guide you through the booking process  
**🗺️ Ask me:** "What do you recommend?" - Activities and services tailored for you  
**✨ Ask me:** Any travel question - I'll use my knowledge to help!

*I'm here to assist with anything you need! 😊*"""
        
        return response
    
    def handle_room_availability(self, message: str, context: Dict):
        """ENHANCED: Handle room availability with date filtering"""
        try:
            # Check if we have dates from the user
            dates = self.extract_dates_from_message(message)
            print(f"DEBUG: Room availability - extracted dates: {dates}")
            
            
            # If no dates provided, ask for them
            if len(dates) < 2:
                if not st.session_state['pending_check_in']:
                    st.session_state['date_collection_step'] = 'check_in'
                    return {
                        "response": """🗓️ **To show you the most accurate room availability, I need your travel dates:**
                        

Please provide your **check-in date** and **check-out date** in the format YYYY-MM-DD.

**Examples:**
• July 15, 2025
• 2025-07-15
• 15/07/2025
• tomorrow
• today

This helps me show you rooms that will definitely be available during your stay! ✨"""
                    }
                elif not st.session_state['pending_check_out']:
                    st.session_state['date_collection_step'] = 'check_out'
                    return {
                        "response": f"""✅ Check-in date recorded: **{st.session_state['pending_check_in']}**

Now please provide your **check-out date** (format: YYYY-MM-DD):"""
                    }
            
            # Process dates
            if len(dates) >= 2:
                check_in_date = dates[0]
                check_out_date = dates[1]
            elif len(dates) == 1 and st.session_state['pending_check_in']:
                check_in_date = st.session_state['pending_check_in']
                check_out_date = dates[0]
            elif len(dates) == 1 and not st.session_state['pending_check_in']:
                st.session_state['pending_check_in'] = dates[0]
                return {
                    "response": f"""✅ Check-in date recorded: **{dates[0]}**

Now please provide your **check-out date** in any format:
**Examples:**
• July 18, 2025
• 2025-07-18
• 18/07/2025
• next week"""
                }
            else:
                check_in_date = st.session_state.get('pending_check_in')
                check_out_date = st.session_state.get('pending_check_out')
            
            # Validate dates
            try:
                from datetime import datetime
                checkin_dt = datetime.strptime(check_in_date, '%Y-%m-%d')
                checkout_dt = datetime.strptime(check_out_date, '%Y-%m-%d')
                
                if checkout_dt <= checkin_dt:
                    st.session_state['pending_check_in'] = None
                    st.session_state['pending_check_out'] = None
                    st.session_state['date_collection_step'] = 'check_in'
                    return {"response": "❌ Check-out date must be after check-in date. Please provide valid dates."}
                
                if checkin_dt < datetime.now():
                    st.session_state['pending_check_in'] = None
                    st.session_state['pending_check_out'] = None
                    st.session_state['date_collection_step'] = 'check_in'
                    return {"response": "❌ Check-in date cannot be in the past. Please provide future dates."}
                    
            except ValueError:
                
                st.session_state['pending_check_in'] = None
                st.session_state['pending_check_out'] = None
                st.session_state['date_collection_step'] = 'check_in'
                return {"response": "❌ Invalid date format. Please use YYYY-MM-DD format (e.g., 2025-07-15)."}
            
            # Clear temporary date storage
            st.session_state['pending_check_in'] = None
            st.session_state['pending_check_out'] = None
            st.session_state['date_collection_step'] = None
            
            print(f"DEBUG: Getting rooms for dates {check_in_date} to {check_out_date}")
            
            # Get filtered rooms
            rooms = self.get_all_rooms(check_in_date, check_out_date)
            
            if rooms:
                print(f"DEBUG: Found {len(rooms)} available rooms after filtering")
                
                # Store room data for table display
                st.session_state['current_room_data'] = rooms
                st.session_state['show_room_table'] = True
                st.session_state['last_search_dates'] = {
                    'check_in': check_in_date,
                    'check_out': check_out_date,
                    'search_timestamp': datetime.now().isoformat()
                    }
                
                # Create summary statistics
                room_types = {}
                price_ranges = {"Budget (₹2,000-3,000)": 0, "Standard (₹3,001-5,000)": 0, 
                               "Premium (₹5,001-8,000)": 0, "Luxury (₹8,001+)": 0}
                
                for room in rooms:
                    room_type = room.get('Room Type', 'Standard')
                    price = float(room.get('Price', 0))
                    
                    # Count room types
                    room_types[room_type] = room_types.get(room_type, 0) + 1
                    
                    # Count price ranges
                    if price <= 3000:
                        price_ranges["Budget (₹2,000-3,000)"] += 1
                    elif price <= 5000:
                        price_ranges["Standard (₹3,001-5,000)"] += 1
                    elif price <= 8000:
                        price_ranges["Premium (₹5,001-8,000)"] += 1
                    else:
                        price_ranges["Luxury (₹8,001+)"] += 1
                
                # Store chart data for rendering
                st.session_state['room_types_data'] = room_types
                st.session_state['price_ranges_data'] = price_ranges
                
                # Create response with date confirmation
                response_text = f"""✅ **Available Rooms for Your Stay ({len(rooms)} total rooms)**

📅 **Your Dates:** {check_in_date} to {check_out_date}
🏨 **Filtered Results:** Showing only rooms available during your entire stay.

**📊 Visual charts and detailed room information are displayed below for easy comparison.**"""
                
                # Add personalized note if guest is identified
                guest_profile = context.get('guest_profile') if context else None
                if guest_profile:
                    previous_room = guest_profile.get('room_type', 'Not specified')
                    response_text += f"\n💡 **Based on your previous {previous_room} stay, ask me: 'Recommend me a room' for personalized suggestions!**"
                    response_text += f"\n📅 **Ready to book?** Just say: 'Book a room' and I'll guide you through the process!"
                else:
                    response_text += f"\n💡 **Load your guest profile for personalized recommendations and easy booking!**"
                
                return {"response": response_text, "available_rooms": rooms, "show_table": True}
            else:
                return {"response": f"""❌ **No rooms available for your requested dates**

📅 **Requested:** {check_in_date} to {check_out_date}

**Suggestions:**
• Try different dates
• Check for shorter stays
• Contact our staff for alternative options

Would you like to search for different dates?"""}
                
        except Exception as e:
            print(f"DEBUG: Exception in room availability: {e}")
            return {"response": f"❌ Error checking room availability: {str(e)}"}
    
    def handle_llm_powered_questions(self, message: str, context: Dict):
        """Handle all other questions using Phi-4-mini's knowledge - ENHANCED FOR NATURAL RECOMMENDATIONS"""
        try:
            if not self.ollama_client.available:
                return {"response": "I'm sorry, my AI knowledge system is not available right now. Please contact our staff for assistance."}
            
            # Get guest context for personalization
            guest_profile = context.get('guest_profile') if context else None
            
            # Create personalized prompt - ENHANCED FOR MUMBAI RECOMMENDATIONS
            if guest_profile:
                guest_name = guest_profile.get('first_name', 'Guest')
                profession = guest_profile.get('profession', 'traveler')
                purpose = guest_profile.get('purpose_of_visit', '')
                amenities_used = guest_profile.get('amenities_used', '')
                activities_booked = guest_profile.get('extra_activities_booked', '')
                origin = guest_profile.get('place_of_origin', '')
                
                # Check if asking for Mumbai recommendations
                personalized_prompt = f"""You are a helpful Mumbai hotel concierge speaking to {guest_name}, a {profession}.
 Guest question: {message}

Provide a natural, helpful response as a knowledgeable concierge would. Be conversational and informative."""
                   
            
            # Generate response using Phi-4-mini
            llm_response = self.ollama_client.generate_response(
                personalized_prompt,
                "You are an experienced Mumbai hotel concierge with deep knowledge of the city. Provide natural, helpful responses based on your knowledge. Be conversational and respond naturally without forced formats."
            )
            
            
            return {"response": llm_response}
            
        except Exception as e:
            return {"response": f"I encountered an error while processing your question: {str(e)}. Please try rephrasing your question."}
    
    def sync_with_staff(self, guest_profile):
        """Sync with staff interface"""
        try:
            sessions_file = "active_guest_sessions.json"
            
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
            else:
                sessions = {}
            
            sessions[st.session_state['session_id']] = {
                "guest_profile": guest_profile,
                "contextual_insights": st.session_state.get('contextual_insights'),
                "last_updated": time.time(),
                "activity": "Active - AI Profile Loaded",
                "conversation_context": st.session_state['conversation_context'][-3:] if st.session_state['conversation_context'] else []
            }
            
            with open(sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
                
        except Exception as e:
            print(f"Sync error: {e}")
    
    def render_interface(self):
        """Main interface"""
        st.title("🏨 Welcome to Hotel Inn")
        st.markdown('<div style="font-size:1.5rem; font-weight:600; margin-bottom: 1.5em;">✨ Presenting to you ✨ - the perfect assistant for all your travel needs! ✨</div>',unsafe_allow_html=True)
        
        # Initialize connection
        if not self.initialize_connection():
            st.stop()
        
        # Show Ollama status
        #if self.ollama_client.available:
            #st.success("🤖 AI Knowledge System (Phi-4-mini) Connected")
        #else:
            #st.warning("⚠️ AI Knowledge System Offline - Basic functions available")
        
        # Sidebar
        with st.sidebar:
            st.header("👤 Guest Identification")
            
            id_method = st.radio("Identify by:", ["Name", "Phone Number"])
            
            if id_method == "Name":
                first_name = st.text_input("First Name", key="fname_input")
                last_name = st.text_input("Last Name", key="lname_input")
                if st.button("🧠 Load Profile"):
                    if first_name and last_name:
                        st.session_state['guest_context'] = {"guest_name": f"{first_name} {last_name}"}
                        st.session_state['guest_identified'] = False
                        st.rerun()
            else:
                phone_number = st.text_input("Phone Number", key="phone_input", placeholder="Enter phone number")
                if st.button("🧠 Load Profile"):
                    st.session_state['guest_context'] = {"phone_number": phone_number}
                    st.session_state['guest_identified'] = False
                    st.rerun()
            
            # Show current guest - ENHANCED WITH BOOKING BUTTONS
            if st.session_state['current_guest_profile']:
                st.divider()
                st.subheader("✅ Current Guest")
                profile = st.session_state['current_guest_profile']
                st.success(f"**{profile['first_name']} {profile['last_name']}**")
                st.write(f"From: {profile.get('place_of_origin', 'Not specified')}")
                st.write(f"Profession: {profile.get('profession', 'Not specified')}")
                st.write(f"Previous Room: {profile.get('room_type', 'First visit')}")
                
                # Quick action buttons - ENHANCED WITH BOOKING
                if st.button("🏨 Show Available Rooms"):
                    st.session_state['mcp_messages'].append({"role": "user", "content": "Show available rooms"})
                    response = self.intelligent_handler("Show available rooms", st.session_state['guest_context'])
                    st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                    st.rerun()
                
                if st.button("🎯 Recommend Me a Room"):
                    st.session_state['mcp_messages'].append({"role": "user", "content": "Recommend me a room based on my previous stay"})
                    response = self.intelligent_handler("Recommend me a room based on my previous stay", st.session_state['guest_context'])
                    st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                    st.rerun()
                
                if st.button("🗺️ Local Recommendations"):
                    question = f"What are the best attractions and restaurants in Mumbai?"
                    st.session_state['mcp_messages'].append({"role": "user", "content": question})
                    response = self.intelligent_handler(question, st.session_state['guest_context'])
                    st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                    st.rerun()
        
        # Display messages
        for message in st.session_state['mcp_messages']:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True )
        
        # Display room availability table if requested - FIXED FILTERING ISSUE
        if (st.session_state.get('show_room_table') and st.session_state.get('current_room_data') and not st.session_state.get('progressive_booking')):
            table_anchor = st.empty()
            st.markdown("---")
            
            # Display charts
            if st.session_state.get('room_types_data') and st.session_state.get('price_ranges_data'):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Room Types Distribution")
                    room_types_data = st.session_state['room_types_data']
                    
                    # Create bar chart for room types
                    fig_bar = px.bar(
                        x=list(room_types_data.keys()),
                        y=list(room_types_data.values()),
                        labels={'x': 'Room Type', 'y': 'Number of Rooms'},
                        title="Available Rooms by Type",
                        color_continuous_scale='viridis'
                    )
                    fig_bar.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with col2:
                    st.subheader("💰 Price Range Distribution")
                    price_ranges_data = st.session_state['price_ranges_data']
                    
                    # Filter out zero values for pie chart
                    filtered_price_data = {k: v for k, v in price_ranges_data.items() if v > 0}
                    
                    # Create pie chart for price ranges
                    fig_pie = px.pie(
                        values=list(filtered_price_data.values()),
                        names=list(filtered_price_data.keys()),
                        title="Price Range Distribution",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("🏨 Available Rooms - Detailed View")
            
            # Prepare data for table
            room_data = []
            for room in st.session_state['current_room_data']:
                room_data.append({
                    'Room Number': room.get('Room Number', 'N/A'),
                    'Room Type': room.get('Room Type', 'Standard'),
                    'Price per Night': f"₹{float(room.get('Price', 0)):,.0f}",
                    #'Status': room.get('Availability', 'Available')
                })
            
            # Create DataFrame
            df = pd.DataFrame(room_data)
            
            # Add filter options with minimum selection validation - FIXED
            col1, col2, col3 = st.columns(3)
            
            with col1:
                room_types = df['Room Type'].unique()
                selected_types = st.multiselect(
                    "Filter by Room Type:", 
                    room_types, 
                    default=room_types,
                    help="Select at least one room type. You can choose specific types like 'Single' or 'Family' only.",
                    key="room_type_filter"
                )
                
                # Ensure minimum of 1 room type is selected
                if not selected_types:
                    st.warning("⚠️ Please select at least one room type to view results.")
                    selected_types = [room_types[0]]  # Default to first room type if none selected
            
            with col2:
                # Price range filter
                price_filter = st.selectbox("Filter by Price Range:", 
                                          ["All Prices", "Budget (₹2,000-3,000)", "Standard (₹3,001-5,000)", 
                                           "Premium (₹5,001-8,000)", "Luxury (₹8,001+)"],
                                          key="price_range_filter")
            
            with col3:
                if st.button("📅 Book a Room"):
                    if st.session_state.get('current_guest_profile'):
                        st.session_state['mcp_messages'].append({"role": "user", "content": "Book a room"})
                        response = self.intelligent_handler("Book a room", st.session_state['guest_context'])
                        st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                        st.rerun()
                    else:
                        st.warning("Please load your guest profile first to book a room.")
            

            # Apply filters and show filtered results - FIXED LOGIC
            if selected_types:
                filtered_df = df[df['Room Type'].isin(selected_types)].copy()
                
                if price_filter != "All Prices":
                    filtered_df['Price_Numeric'] = filtered_df['Price per Night'].str.replace('₹', '').str.replace(',', '').astype(int)
                    
                    if price_filter == "Budget (₹2,000-3,000)":
                        filtered_df = filtered_df[filtered_df['Price_Numeric'] <= 3000]
                    elif price_filter == "Standard (₹3,001-5,000)":
                        filtered_df = filtered_df[(filtered_df['Price_Numeric'] > 3000) & 
                                        (filtered_df['Price_Numeric'] <= 5000)]
                    elif price_filter == "Premium (₹5,001-8,000)":
                        filtered_df = filtered_df[(filtered_df['Price_Numeric'] > 5000) & 
                                        (filtered_df['Price_Numeric'] <= 8000)]
                    elif price_filter == "Luxury (₹8,001+)":
                        filtered_df = filtered_df[filtered_df['Price_Numeric'] > 8000]
                    
                    if 'Price_Numeric' in filtered_df.columns:
                        filtered_df = filtered_df.drop('Price_Numeric', axis=1)
                display_df = filtered_df
            else:
                display_df = df  
                
            # Single table display
            filters_applied = (len(selected_types) != len(room_types)) or (price_filter != "All Prices")
            if filters_applied:
                st.subheader(f"🔍 Filtered Results ({len(display_df)} rooms)")
            else:
                st.subheader("🏨 Available Rooms - Detailed View")  
            
            if len(display_df) > 0:
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Room Number": st.column_config.TextColumn("Room Number", width="small"),
                        "Room Type": st.column_config.TextColumn("Room Type", width="medium"),
                         "Price per Night": st.column_config.TextColumn("Price per Night", width="medium")
                    }
                )
                
            else:
                st.info("No rooms match your current filter criteria. Please adjust your filters.")
                
        
        # Auto-identify guest
        if st.session_state['guest_context'] and not st.session_state['guest_identified']:
            context = st.session_state['guest_context']
            
            if context.get('guest_name'):
                identifier = context['guest_name']
            elif context.get('phone_number'):
                identifier=f"phone number {context['phone_number']}"
            else:
                identifier = f"guest ID {context.get('guest_id', 'Unknown')}"
            
            prompt = f"Load my profile - I'm {identifier}"
            
            st.session_state['mcp_messages'].append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("🧠 Loading your profile..."):
                    response = self.intelligent_handler(prompt, context)
                    st.markdown(response["response"])
                    st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                    
                    if response.get("guest_profile"):
                        st.session_state['current_guest_profile'] = response["guest_profile"]
                        st.session_state['guest_context']['guest_profile'] = response["guest_profile"]
                        if response.get("contextual_insights"):
                            st.session_state['contextual_insights'] = response["contextual_insights"]
            
            st.session_state['guest_identified'] = True
            st.rerun()
        
        # Chat input - ENHANCED
        if prompt := st.chat_input("Try: 'show available rooms', 'recommend me a room', 'what do you recommend?', or any travel question..."):
            st.session_state['mcp_messages'].append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("🧠 Processing with AI..."):
                    response = self.intelligent_handler(prompt, st.session_state['guest_context'])
                    st.markdown(response["response"])
                    st.session_state['mcp_messages'].append({"role": "assistant", "content": response["response"]})
                    
                    # Trigger table display if room data is returned
                    if response.get("show_table"):
                        st.rerun()


def main():
    agent = IntelligentHotelAgent()
    agent.render_interface()


if __name__ == "__main__":
    main()

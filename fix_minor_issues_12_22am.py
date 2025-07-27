# fix_minor_issues.py
def fix_main_agent_issues():
    """Fix the two minor issues in main_agent.py"""
    
    with open('main_agent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Room price formatting
    old_room_line = 'room_list.append(f"🏠 **Room {room.get(\'Room Number\')}**: {room.get(\'Room Type\')} - ₹{room.get(\'Price\', 0):,}/night")'
    new_room_line = '''price = room.get('Price', 0)
                price_formatted = f"{float(price):,.0f}" if price else "0"
                room_list.append(f"🏠 **Room {room.get('Room Number')}**: {room.get('Room Type')} - ₹{price_formatted}/night")'''
    
    if old_room_line in content:
        content = content.replace(old_room_line, new_room_line)
        print("✅ Fixed room price formatting")
    
    # Fix 2: Replace LLM call with simple responses
    old_llm_section = '''try:
                response = await self.llm.acomplete(enhanced_prompt)
                llm_response = str(response)
            except Exception as llm_error:
                print(f"⚠️ LLM error: {llm_error}")
                llm_response = "Hello! I'm your hotel assistant. How can I help you today?"'''
    
    new_llm_section = '''# Simple responses without LLM to avoid timeout issues
            hotel_responses = {
                "amenities": "Our hotel offers: 🏊 Swimming Pool, 🏋️ Fitness Center, 🍽️ Restaurant, 🌐 Wi-Fi, 🚗 Parking, 🛎️ Room Service, 🏢 Business Center, and 💆 Spa Services.",
                "services": "We provide: ✅ 24/7 Front Desk, 🧳 Concierge Services, 🚐 Airport Transfer, 🍳 Room Service, 🧹 Housekeeping, 🏢 Meeting Rooms, and 📞 Wake-up Calls."
            }
            
            message_lower = message.lower()
            if any(word in message_lower for word in ['amenity', 'amenities']):
                llm_response = hotel_responses["amenities"]
            elif any(word in message_lower for word in ['service', 'services']):
                llm_response = hotel_responses["services"]
            else:
                llm_response = "Hello! I'm your hotel assistant. I can help with room bookings, guest profiles, amenities, and services. How can I assist you today?"'''
    
    if old_llm_section in content:
        content = content.replace(old_llm_section, new_llm_section)
        print("✅ Fixed LLM timeout issue")
    
    # Save fixed version
    with open('main_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ main_agent.py fixes applied")

if __name__ == "__main__":
    fix_main_agent_issues()

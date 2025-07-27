# hotel_mcp_sse_server.py - CONTEXT-DRIVEN PERSONALIZATION ENGINE
import asyncio
import json
import requests
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hotel-mcp-context-server")

class ContextAwareHotelMCPServer:
    def __init__(self):
        self.app = FastAPI(title="Context-Aware Hotel MCP Server")
        self.setup_routes()
        logger.info("🧠 Context-Aware Hotel MCP Server initialized")
    
    def setup_routes(self):
        """Setup FastAPI routes for context-aware SSE transport"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Context-Aware Hotel MCP Server", "transport": "sse", "status": "running"}
        
        @self.app.post("/sse")
        async def handle_mcp_request(request_data: dict):
            """Handle MCP requests with context awareness"""
            try:
                method = request_data.get("method")
                params = request_data.get("params", {})
                
                if method == "tools/list":
                    return await self.list_context_tools()
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    return await self.call_context_tool(tool_name, arguments)
                elif method == "initialize":
                    return {"result": {"protocolVersion": "2024-11-05", "capabilities": {"contextAware": True}}}
                else:
                    return {"error": f"Unknown method: {method}"}
                    
            except Exception as e:
                logger.error(f"Request error: {e}")
                return {"error": str(e)}
    
    async def list_context_tools(self):
        """List context-aware MCP tools"""
        tools = [
            {
                "name": "get_contextual_guest_profile",
                "description": "Get complete guest profile with deep contextual analysis of preferences, behavior patterns, and feedback history",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guest_id": {"type": "integer"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"}
                    }
                }
            },
            {
                "name": "generate_autonomous_recommendations",
                "description": "AI-powered autonomous recommendations based on room_type, special_requests, amenities_used, profession, activities, loyalty, payment patterns, and feedback",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guest_profile": {"type": "object", "required": True},
                        "context_focus": {"type": "string", "enum": ["profession_based", "activity_based", "feedback_based", "loyalty_based", "comprehensive"]}
                    }
                }
            },
            {
                "name": "contextual_room_booking",
                "description": "Context-aware room booking with intelligent upselling based on guest behavior patterns and preferences",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guest_id": {"type": "integer", "required": True},
                        "room_number": {"type": "integer", "required": True},
                        "check_in_date": {"type": "string", "required": True},
                        "check_out_date": {"type": "string", "required": True},
                        "number_of_adults": {"type": "integer", "required": True}
                    }
                }
            },
            {
                "name": "analyze_guest_context_deeply",
                "description": "Deep analysis of guest context using feedback, special requests, amenities usage, and behavioral patterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guest_profile": {"type": "object", "required": True},
                        "analysis_type": {"type": "string", "enum": ["behavioral", "preference", "satisfaction", "loyalty_prediction"]}
                    }
                }
            }
        ]
        
        return {"result": {"tools": tools}}
    
    async def call_context_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute context-aware MCP tool"""
        try:
            logger.info(f"🧠 Context Tool called: {tool_name} with {arguments}")
            
            if tool_name == "get_contextual_guest_profile":
                result = await self._get_contextual_guest_profile(arguments)
            elif tool_name == "generate_autonomous_recommendations":
                result = await self._generate_autonomous_recommendations(arguments)
            elif tool_name == "contextual_room_booking":
                result = await self._contextual_room_booking(arguments)
            elif tool_name == "analyze_guest_context_deeply":
                result = await self._analyze_guest_context_deeply(arguments)
            else:
                result = {"error": f"Unknown context tool: {tool_name}"}
            
            logger.info(f"✅ Context tool result: {result}")
            return {"result": result}
            
        except Exception as e:
            logger.error(f"❌ Context tool error: {e}")
            return {"error": f"Context tool execution failed: {str(e)}"}
    
    async def _get_contextual_guest_profile(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get guest profile with deep contextual analysis"""
        try:
            # Get basic profile
            if args.get("guest_id"):
                response = requests.get(f"http://localhost:8001/guest/by-id/{args['guest_id']}", timeout=10)
            elif args.get("first_name") and args.get("last_name"):
                params = {"first_name": args["first_name"], "last_name": args["last_name"]}
                response = requests.get("http://localhost:8001/guest/by-name", params=params, timeout=10)
            else:
                return {"error": "Must provide guest identification"}
            
            if response.status_code == 200:
                guest_data = response.json()
                
                # DEEP CONTEXTUAL ANALYSIS using the specified columns
                contextual_profile = self._perform_deep_context_analysis(guest_data)
                
                # Combine with enhanced profile
                enhanced_profile = {
                    **guest_data,
                    "contextual_insights": contextual_profile,
                    "recommendation_drivers": self._identify_recommendation_drivers(guest_data)
                }
                
                logger.info(f"✅ Contextual profile loaded for: {guest_data.get('first_name')} {guest_data.get('last_name')}")
                return {"success": True, "guest_profile": enhanced_profile}
            else:
                return {"error": f"Guest not found: HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Contextual profile error: {e}")
            return {"error": f"Failed to get contextual profile: {str(e)}"}
    
    def _perform_deep_context_analysis(self, guest_data):
        """Perform deep analysis of the key contextual columns"""
        
        # Extract key contextual data
        room_type = guest_data.get('room_type', '').lower()
        special_requests = guest_data.get('special_requests', '').lower()
        amenities_used = guest_data.get('amenities_used', '').lower()
        profession = guest_data.get('profession', '').lower()
        extra_activities = guest_data.get('extra_activities_booked', '').lower()
        loyalty_member = guest_data.get('loyalty_member', 'New')
        payment_method = guest_data.get('payment_method', '').lower()
        total_bill = guest_data.get('total_bill', 0)
        feedback = guest_data.get('feedback_and_issues', '').lower()
        
        analysis = {
            "room_preferences": self._analyze_room_preferences(room_type, special_requests),
            "lifestyle_profile": self._analyze_lifestyle(profession, amenities_used, extra_activities),
            "satisfaction_insights": self._analyze_satisfaction(feedback, special_requests),
            "loyalty_behavior": self._analyze_loyalty_behavior(loyalty_member, total_bill, payment_method),
            "service_patterns": self._analyze_service_patterns(amenities_used, extra_activities, special_requests),
            "personality_indicators": self._analyze_personality_indicators(special_requests, feedback, profession)
        }
        
        return analysis
    
    def _analyze_room_preferences(self, room_type, special_requests):
        """Analyze room preferences from room_type and special_requests"""
        preferences = {
            "room_category": "standard",
            "space_preference": "moderate",
            "privacy_level": "standard",
            "luxury_inclination": "moderate",
            "special_needs": []
        }
        
        # Room type analysis
        if any(word in room_type for word in ['suite', 'presidential', 'executive']):
            preferences["room_category"] = "luxury"
            preferences["space_preference"] = "spacious"
            preferences["luxury_inclination"] = "high"
        elif any(word in room_type for word in ['deluxe', 'premium', 'superior']):
            preferences["room_category"] = "premium"
            preferences["luxury_inclination"] = "moderate-high"
        
        # Special requests analysis
        if special_requests:
            if any(word in special_requests for word in ['quiet', 'silent', 'peaceful']):
                preferences["special_needs"].append("noise_sensitive")
            if any(word in special_requests for word in ['view', 'window', 'balcony']):
                preferences["special_needs"].append("view_important")
            if any(word in special_requests for word in ['floor', 'high', 'top']):
                preferences["special_needs"].append("floor_preference")
            if any(word in special_requests for word in ['accessible', 'disability', 'wheelchair']):
                preferences["special_needs"].append("accessibility_needs")
            if any(word in special_requests for word in ['early', 'late', 'check']):
                preferences["special_needs"].append("flexible_timing")
        
        return preferences
    
    def _analyze_lifestyle(self, profession, amenities_used, extra_activities):
        """Analyze lifestyle from profession, amenities_used, and extra_activities_booked"""
        lifestyle = {
            "activity_level": "moderate",
            "wellness_focus": "low",
            "business_orientation": "low",
            "social_preference": "moderate",
            "interests": []
        }
        
        # Profession-based analysis
        if any(word in profession for word in ['executive', 'manager', 'director', 'ceo', 'business']):
            lifestyle["business_orientation"] = "high"
            lifestyle["interests"].extend(["business_facilities", "executive_services", "networking"])
        elif any(word in profession for word in ['doctor', 'engineer', 'consultant', 'lawyer']):
            lifestyle["business_orientation"] = "moderate-high"
            lifestyle["interests"].extend(["professional_services", "quiet_environment"])
        elif any(word in profession for word in ['teacher', 'nurse', 'social']):
            lifestyle["social_preference"] = "high"
            lifestyle["interests"].extend(["community_activities", "social_spaces"])
        
        # Amenities analysis
        if amenities_used:
            if any(word in amenities_used for word in ['spa', 'massage', 'wellness', 'gym', 'fitness']):
                lifestyle["wellness_focus"] = "high"
                lifestyle["activity_level"] = "high"
                lifestyle["interests"].extend(["wellness", "fitness", "relaxation"])
            if any(word in amenities_used for word in ['pool', 'swimming']):
                lifestyle["activity_level"] = "moderate-high"
                lifestyle["interests"].append("recreational_swimming")
            if any(word in amenities_used for word in ['business', 'meeting', 'conference']):
                lifestyle["business_orientation"] = "high"
                lifestyle["interests"].extend(["business_facilities", "meeting_spaces"])
        
        # Activities analysis
        if extra_activities:
            if any(word in extra_activities for word in ['tour', 'sightseeing', 'cultural']):
                lifestyle["social_preference"] = "high"
                lifestyle["interests"].extend(["cultural_experiences", "local_tours"])
            if any(word in extra_activities for word in ['adventure', 'sports', 'hiking']):
                lifestyle["activity_level"] = "high"
                lifestyle["interests"].extend(["adventure_sports", "outdoor_activities"])
            if any(word in extra_activities for word in ['dining', 'restaurant', 'food']):
                lifestyle["interests"].append("culinary_experiences")
        
        return lifestyle
    
    def _analyze_satisfaction(self, feedback, special_requests):
        """Analyze satisfaction patterns from feedback and special requests"""
        satisfaction = {
            "overall_sentiment": "neutral",
            "service_sensitivity": "moderate",
            "complaint_patterns": [],
            "praise_patterns": [],
            "attention_to_detail": "moderate"
        }
        
        if feedback:
            # Positive indicators
            if any(word in feedback for word in ['excellent', 'amazing', 'perfect', 'loved', 'wonderful']):
                satisfaction["overall_sentiment"] = "very_positive"
            elif any(word in feedback for word in ['good', 'nice', 'pleasant', 'satisfied']):
                satisfaction["overall_sentiment"] = "positive"
            
            # Negative indicators
            elif any(word in feedback for word in ['terrible', 'awful', 'horrible', 'worst']):
                satisfaction["overall_sentiment"] = "very_negative"
            elif any(word in feedback for word in ['bad', 'poor', 'disappointed', 'unsatisfied']):
                satisfaction["overall_sentiment"] = "negative"
            
            # Service sensitivity indicators
            if any(word in feedback for word in ['staff', 'service', 'attitude', 'helpful']):
                satisfaction["service_sensitivity"] = "high"
            
            # Complaint patterns
            if any(word in feedback for word in ['noise', 'loud', 'disturbing']):
                satisfaction["complaint_patterns"].append("noise_issues")
            if any(word in feedback for word in ['dirty', 'clean', 'hygiene']):
                satisfaction["complaint_patterns"].append("cleanliness_issues")
            if any(word in feedback for word in ['slow', 'wait', 'delay']):
                satisfaction["complaint_patterns"].append("service_speed_issues")
        
        # Special requests indicate attention to detail
        if special_requests and len(special_requests) > 20:
            satisfaction["attention_to_detail"] = "high"
        
        return satisfaction
    
    def _analyze_loyalty_behavior(self, loyalty_member, total_bill, payment_method):
        """Analyze loyalty behavior from loyalty status, spending, and payment patterns"""
        loyalty_analysis = {
            "loyalty_tier": loyalty_member,
            "spending_category": "moderate",
            "payment_behavior": "standard",
            "value_perception": "moderate",
            "retention_probability": "moderate"
        }
        
        # Spending analysis
        if total_bill > 20000:
            loyalty_analysis["spending_category"] = "high"
            loyalty_analysis["value_perception"] = "high"
        elif total_bill > 10000:
            loyalty_analysis["spending_category"] = "moderate-high"
        elif total_bill < 3000:
            loyalty_analysis["spending_category"] = "budget"
            loyalty_analysis["value_perception"] = "price_sensitive"
        
        # Loyalty tier analysis
        if loyalty_member in ['Gold', 'Platinum', 'Diamond']:
            loyalty_analysis["retention_probability"] = "high"
        elif loyalty_member in ['Silver', 'Bronze']:
            loyalty_analysis["retention_probability"] = "moderate-high"
        elif loyalty_member == 'New':
            loyalty_analysis["retention_probability"] = "opportunity"
        
        # Payment method insights
        if 'credit' in payment_method.lower():
            loyalty_analysis["payment_behavior"] = "convenient"
        elif 'cash' in payment_method.lower():
            loyalty_analysis["payment_behavior"] = "traditional"
        
        return loyalty_analysis
    
    def _analyze_service_patterns(self, amenities_used, extra_activities, special_requests):
        """Analyze service usage patterns"""
        patterns = {
            "service_usage_level": "moderate",
            "service_categories": [],
            "engagement_style": "moderate",
            "service_expectations": "standard"
        }
        
        service_count = 0
        
        if amenities_used:
            service_count += len(amenities_used.split(','))
            if any(word in amenities_used for word in ['spa', 'massage', 'wellness']):
                patterns["service_categories"].append("wellness")
            if any(word in amenities_used for word in ['business', 'meeting']):
                patterns["service_categories"].append("business")
            if any(word in amenities_used for word in ['dining', 'restaurant']):
                patterns["service_categories"].append("dining")
        
        if extra_activities:
            service_count += len(extra_activities.split(','))
            patterns["service_categories"].append("experiential")
        
        if special_requests:
            service_count += 1
            patterns["service_expectations"] = "detailed"
        
        if service_count > 5:
            patterns["service_usage_level"] = "high"
            patterns["engagement_style"] = "active"
        elif service_count > 2:
            patterns["service_usage_level"] = "moderate-high"
        
        return patterns
    
    def _analyze_personality_indicators(self, special_requests, feedback, profession):
        """Analyze personality indicators"""
        personality = {
            "communication_style": "standard",
            "detail_orientation": "moderate",
            "social_preference": "moderate",
            "assertiveness": "moderate"
        }
        
        # Detail orientation from special requests
        if special_requests and len(special_requests) > 30:
            personality["detail_orientation"] = "high"
        elif special_requests and len(special_requests) > 10:
            personality["detail_orientation"] = "moderate-high"
        
        # Communication style from feedback
        if feedback:
            if len(feedback) > 100:
                personality["communication_style"] = "expressive"
            if any(word in feedback for word in ['please', 'thank', 'appreciate']):
                personality["communication_style"] = "polite"
            if any(word in feedback for word in ['must', 'should', 'need', 'require']):
                personality["assertiveness"] = "high"
        
        return personality
    
    def _identify_recommendation_drivers(self, guest_data):
        """Identify key drivers for recommendations"""
        drivers = []
        
        loyalty = guest_data.get('loyalty_member', 'New')
        profession = guest_data.get('profession', '').lower()
        amenities = guest_data.get('amenities_used', '').lower()
        activities = guest_data.get('extra_activities_booked', '').lower()
        total_bill = guest_data.get('total_bill', 0)
        
        # Primary drivers
        if loyalty in ['Gold', 'Platinum', 'Diamond']:
            drivers.append(f"VIP_{loyalty}_status")
        
        if total_bill > 15000:
            drivers.append("high_value_guest")
        elif total_bill > 8000:
            drivers.append("moderate_value_guest")
        
        if 'business' in profession or 'executive' in profession:
            drivers.append("business_professional")
        
        if any(word in amenities for word in ['spa', 'wellness', 'massage']):
            drivers.append("wellness_focused")
        
        if any(word in activities for word in ['tour', 'cultural', 'adventure']):
            drivers.append("experience_seeker")
        
        return drivers
    
    async def _generate_autonomous_recommendations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate autonomous AI-powered recommendations based on deep context"""
        try:
            guest_profile = args.get("guest_profile", {})
            context_focus = args.get("context_focus", "comprehensive")
            
            if not guest_profile:
                return {"error": "Guest profile required for autonomous recommendations"}
            
            # Extract contextual insights
            contextual_insights = guest_profile.get("contextual_insights", {})
            recommendation_drivers = guest_profile.get("recommendation_drivers", [])
            
            # Generate context-driven recommendations
            recommendations = self._generate_context_driven_recommendations(
                guest_profile, contextual_insights, recommendation_drivers, context_focus
            )
            
            logger.info(f"✅ Generated autonomous recommendations for {guest_profile.get('first_name')}")
            return {
                "success": True,
                "recommendations": recommendations,
                "context_focus": context_focus,
                "driven_by": recommendation_drivers
            }
            
        except Exception as e:
            logger.error(f"❌ Autonomous recommendations error: {e}")
            return {"error": f"Failed to generate autonomous recommendations: {str(e)}"}
    
    def _generate_context_driven_recommendations(self, guest_profile, contextual_insights, drivers, focus):
        """Generate recommendations driven by contextual analysis"""
        
        # Base guest data
        first_name = guest_profile.get('first_name', 'Guest')
        loyalty = guest_profile.get('loyalty_member', 'New')
        total_bill = guest_profile.get('total_bill', 0)
        profession = guest_profile.get('profession', '')
        
        # Contextual data
        room_prefs = contextual_insights.get("room_preferences", {})
        lifestyle = contextual_insights.get("lifestyle_profile", {})
        satisfaction = contextual_insights.get("satisfaction_insights", {})
        loyalty_behavior = contextual_insights.get("loyalty_behavior", {})
        
        recommendations = {
            "autonomous_message": "",
            "contextual_room_recommendations": [],
            "lifestyle_based_services": [],
            "profession_driven_amenities": [],
            "satisfaction_optimized_experiences": [],
            "loyalty_exclusive_offers": [],
            "context_explanation": ""
        }
        
        # AUTONOMOUS MESSAGE based on deep context
        recommendations["autonomous_message"] = f"""🎯 **AI-Powered Personalized Recommendations for {first_name}**

Based on my analysis of your profile, I've identified these key insights:
• **Room Preference:** {room_prefs.get('room_category', 'Standard')} category with {room_prefs.get('luxury_inclination', 'moderate')} luxury inclination
• **Lifestyle:** {lifestyle.get('activity_level', 'Moderate')} activity level, {lifestyle.get('wellness_focus', 'moderate')} wellness focus
• **Professional Context:** {profession} - indicating {lifestyle.get('business_orientation', 'moderate')} business orientation
• **Service Pattern:** {loyalty_behavior.get('spending_category', 'moderate')} spending profile with {satisfaction.get('service_sensitivity', 'moderate')} service sensitivity

Here are my intelligent recommendations tailored specifically for you:"""
        
        # CONTEXTUAL ROOM RECOMMENDATIONS
        if room_prefs.get("luxury_inclination") == "high" or "high_value_guest" in drivers:
            recommendations["contextual_room_recommendations"] = [
                {
                    "name": "Presidential Suite",
                    "price": 18000,
                    "context_match": f"Perfect for your {room_prefs.get('room_category', 'luxury')} preferences and {loyalty} status",
                    "why_autonomous": f"AI detected high luxury inclination from your {guest_profile.get('room_type', 'previous')} room choice"
                },
                {
                    "name": "Executive Floor Deluxe",
                    "price": 12000,
                    "context_match": f"Matches your {lifestyle.get('business_orientation', 'professional')} orientation and service expectations",
                    "why_autonomous": f"Recommended based on your {profession} profession and service usage patterns"
                }
            ]
        elif "business_professional" in drivers:
            recommendations["contextual_room_recommendations"] = [
                {
                    "name": "Business Deluxe Room",
                    "price": 8500,
                    "context_match": f"Optimized for {profession} professionals with business amenities",
                    "why_autonomous": "AI identified business orientation from profession and amenity usage"
                }
            ]
        else:
            recommendations["contextual_room_recommendations"] = [
                {
                    "name": "Superior Comfort Room",
                    "price": 6000,
                    "context_match": f"Balanced comfort for your {lifestyle.get('activity_level', 'moderate')} lifestyle",
                    "why_autonomous": "AI matched room to your activity level and preferences"
                }
            ]
        
        # LIFESTYLE-BASED SERVICES
        if "wellness_focused" in drivers or lifestyle.get("wellness_focus") == "high":
            recommendations["lifestyle_based_services"] = [
                {
                    "name": "Comprehensive Wellness Package",
                    "price": 4500,
                    "context_match": f"Matches your wellness focus from {guest_profile.get('amenities_used', 'spa usage')}",
                    "why_autonomous": "AI detected strong wellness preference from amenity usage patterns"
                },
                {
                    "name": "Personal Fitness Trainer Session",
                    "price": 2000,
                    "context_match": f"Complements your {lifestyle.get('activity_level', 'active')} lifestyle",
                    "why_autonomous": "Recommended based on fitness facility usage history"
                }
            ]
        
        if lifestyle.get("business_orientation") == "high":
            recommendations["lifestyle_based_services"].extend([
                {
                    "name": "Executive Concierge Service",
                    "price": 1500,
                    "context_match": f"Essential for {profession} professionals",
                    "why_autonomous": "AI identified business travel patterns and professional needs"
                }
            ])
        
        # PROFESSION-DRIVEN AMENITIES
        profession_lower = profession.lower()
        if any(word in profession_lower for word in ['executive', 'manager', 'director', 'ceo']):
            recommendations["profession_driven_amenities"] = [
                {
                    "name": "Executive Lounge Access",
                    "price": 800,
                    "context_match": f"Standard for {profession} level professionals",
                    "why_autonomous": "AI matched your executive profession with appropriate amenities"
                },
                {
                    "name": "Priority Business Services",
                    "price": 1200,
                    "context_match": "Fast-track services for executive efficiency",
                    "why_autonomous": "Recommended based on executive-level professional needs"
                }
            ]
        elif any(word in profession_lower for word in ['doctor', 'engineer', 'consultant']):
            recommendations["profession_driven_amenities"] = [
                {
                    "name": "Quiet Zone Premium Access",
                    "price": 500,
                    "context_match": f"Ideal for {profession} requiring focused environment",
                    "why_autonomous": "AI identified need for quiet spaces based on your profession"
                }
            ]
        
        # SATISFACTION-OPTIMIZED EXPERIENCES
        if satisfaction.get("service_sensitivity") == "high":
            recommendations["satisfaction_optimized_experiences"] = [
                {
                    "name": "Dedicated Guest Relations Manager",
                    "price": 1000,
                    "context_match": "Personal attention matching your service expectations",
                    "why_autonomous": f"AI detected high service sensitivity from {guest_profile.get('feedback_and_issues', 'feedback patterns')}"
                }
            ]
        
        if any(word in guest_profile.get('special_requests', '').lower() for word in ['quiet', 'peaceful']):
            recommendations["satisfaction_optimized_experiences"].append({
                "name": "Soundproof Room Guarantee",
                "price": 500,
                "context_match": "Addresses your specific quiet environment needs",
                "why_autonomous": f"AI identified noise sensitivity from special requests: '{guest_profile.get('special_requests', '')}'"
            })
        
        # LOYALTY EXCLUSIVE OFFERS
        if loyalty in ['Gold', 'Platinum', 'Diamond']:
            recommendations["loyalty_exclusive_offers"] = [
                {
                    "name": f"Complimentary {loyalty} Member Upgrade",
                    "price": 0,
                    "context_match": f"Exclusive {loyalty} member privilege",
                    "why_autonomous": f"AI-triggered VIP treatment for {loyalty} status member"
                },
                {
                    "name": "Loyalty Dining Credit",
                    "price": 0,
                    "context_match": f"₹{total_bill//10} dining credit based on spending history",
                    "why_autonomous": f"AI calculated loyalty reward based on ₹{total_bill:,} lifetime spending"
                }
            ]
        
        # CONTEXT EXPLANATION
        recommendations["context_explanation"] = f"""
🧠 **AI Context Analysis Summary:**

**From Room Type & Special Requests:** Identified {room_prefs.get('room_category', 'standard')} preference with {len(room_prefs.get('special_needs', []))} specific needs
**From Profession & Amenities:** Detected {lifestyle.get('business_orientation', 'moderate')} business focus and {lifestyle.get('wellness_focus', 'moderate')} wellness interest
**From Feedback & Satisfaction:** Analyzed {satisfaction.get('overall_sentiment', 'neutral')} sentiment with {satisfaction.get('service_sensitivity', 'moderate')} service sensitivity
**From Loyalty & Spending:** Categorized as {loyalty_behavior.get('spending_category', 'moderate')} value guest with {loyalty_behavior.get('retention_probability', 'moderate')} retention probability

**Primary Recommendation Drivers:** {', '.join(drivers) if drivers else 'Standard guest profile'}
"""
        
        return recommendations
    
    async def _contextual_room_booking(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Context-aware room booking with intelligent pricing and upselling"""
        try:
            # Get guest profile for context
            guest_id = args["guest_id"]
            guest_response = requests.get(f"http://localhost:8001/guest/by-id/{guest_id}", timeout=10)
            
            if guest_response.status_code != 200:
                return {"error": "Could not retrieve guest context for booking"}
            
            guest_data = guest_response.json()
            
            # Perform contextual analysis
            contextual_insights = self._perform_deep_context_analysis(guest_data)
            
            # Standard booking
            booking_data = {
                "guest_id": args["guest_id"],
                "room_number": args["room_number"],
                "check_in_date": args["check_in_date"],
                "check_out_date": args["check_out_date"],
                "number_of_adults": args["number_of_adults"],
                "purpose_of_visit": guest_data.get('purpose_of_visit', 'Leisure')
            }
            
            response = requests.post(
                "http://localhost:8002/bookings/create",
                json=booking_data,
                timeout=15
            )
            
            if response.status_code == 200:
                booking_result = response.json()
                
                # Generate contextual upselling suggestions
                upsell_suggestions = self._generate_contextual_upsells(guest_data, contextual_insights, booking_result)
                
                enhanced_result = {
                    **booking_result,
                    "contextual_upsells": upsell_suggestions,
                    "guest_context_applied": True,
                    "ai_insights": contextual_insights.get("loyalty_behavior", {}),
                    "success": True,
                    "booking_confirmed": True
                }
                
                return enhanced_result
            else:
                return {"success": False, "error": f"Booking failed: HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": f"Contextual booking error: {str(e)}"}
    
    def _generate_contextual_upsells(self, guest_data, contextual_insights, booking_result):
        """Generate contextual upselling suggestions based on guest analysis"""
        upsells = []
        
        loyalty = guest_data.get('loyalty_member', 'New')
        lifestyle = contextual_insights.get("lifestyle_profile", {})
        room_prefs = contextual_insights.get("room_preferences", {})
        
        # Upsell based on lifestyle
        if lifestyle.get("wellness_focus") == "high":
            upsells.append({
                "service": "Spa Package Addition",
                "price": 3000,
                "reasoning": f"Perfect complement to your booking based on your {guest_data.get('amenities_used', 'wellness')} usage"
            })
        
        # Upsell based on loyalty
        if loyalty in ['Gold', 'Platinum']:
            upsells.append({
                "service": f"{loyalty} Member Room Upgrade",
                "price": 2000,
                "reasoning": f"Exclusive {loyalty} member upgrade available for your stay"
            })
        
        # Upsell based on profession
        profession = guest_data.get('profession', '').lower()
        if any(word in profession for word in ['executive', 'manager', 'business']):
            upsells.append({
                "service": "Business Executive Package",
                "price": 1500,
                "reasoning": f"Tailored for {guest_data.get('profession', 'business')} professionals"
            })
        
        return upsells
    
    async def _analyze_guest_context_deeply(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Deep contextual analysis of guest behavior and preferences"""
        try:
            guest_profile = args.get("guest_profile", {})
            analysis_type = args.get("analysis_type", "comprehensive")
            
            if not guest_profile:
                return {"error": "Guest profile required for context analysis"}
            
            # Perform deep analysis
            contextual_insights = self._perform_deep_context_analysis(guest_profile)
            
            # Generate behavioral predictions
            predictions = self._generate_behavioral_predictions(guest_profile, contextual_insights)
            
            return {
                "success": True,
                "contextual_insights": contextual_insights,
                "behavioral_predictions": predictions,
                "analysis_type": analysis_type,
                "confidence_score": self._calculate_confidence_score(guest_profile)
            }
            
        except Exception as e:
            return {"error": f"Context analysis failed: {str(e)}"}
    
    def _generate_behavioral_predictions(self, guest_profile, contextual_insights):
        """Generate predictions about guest behavior"""
        predictions = {
            "likely_to_return": "moderate",
            "upsell_receptivity": "moderate",
            "service_utilization": "moderate",
            "satisfaction_probability": "high",
            "recommendation_likelihood": "moderate"
        }
        
        loyalty = guest_profile.get('loyalty_member', 'New')
        total_bill = guest_profile.get('total_bill', 0)
        satisfaction = contextual_insights.get("satisfaction_insights", {})
        loyalty_behavior = contextual_insights.get("loyalty_behavior", {})
        
        # Return likelihood
        if loyalty in ['Gold', 'Platinum'] and total_bill > 10000:
            predictions["likely_to_return"] = "high"
        elif satisfaction.get("overall_sentiment") == "very_positive":
            predictions["likely_to_return"] = "high"
        
        # Upsell receptivity
        if loyalty_behavior.get("spending_category") == "high":
            predictions["upsell_receptivity"] = "high"
        elif satisfaction.get("service_sensitivity") == "high":
            predictions["upsell_receptivity"] = "moderate-high"
        
        return predictions
    
    def _calculate_confidence_score(self, guest_profile):
        """Calculate confidence score for analysis"""
        score = 0.5  # Base score
        
        # Increase confidence based on data richness
        if guest_profile.get('special_requests'):
            score += 0.1
        if guest_profile.get('amenities_used'):
            score += 0.1
        if guest_profile.get('extra_activities_booked'):
            score += 0.1
        if guest_profile.get('feedback_and_issues'):
            score += 0.2
        if guest_profile.get('total_bill', 0) > 0:
            score += 0.1
        
        return min(score, 1.0)

if __name__ == "__main__":
    server = ContextAwareHotelMCPServer()
    logger.info("🚀 Starting Context-Aware Hotel MCP Server on port 8003...")
    uvicorn.run(server.app, host="localhost", port=8003)

# start_system.py - Context-Aware Hotel MCP System Startup
import subprocess
import time
import sys
import os
import asyncio
import aiohttp
import json
import requests

class ContextAwareHotelSystemStarter:
    def __init__(self):
        self.guest_server = None
        self.booking_server = None
        self.context_mcp_server = None  # UPDATED: Context-aware MCP server
        self.required_files = [
            "guest_profile_server.py",
            "booking_server.py", 
            "hotel_mcp_sse_server.py",  # UPDATED: Context-aware server
            "guest_interface.py",       # Contains embedded client
            "staff_interface.py",       # Contains embedded client
            "Guest_profile_data.csv",
            "Hotel_data_updated.csv"
        ]
        # REMOVED: sse_client_agent.py (not needed - embedded in interfaces)
    
    def check_prerequisites(self):
        """Check if all required files exist"""
        print("🔍 Checking Prerequisites...")
        
        missing_files = []
        for file in self.required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print("❌ Missing Files:")
            for file in missing_files:
                print(f"   - {file}")
            return False
        
        print("✅ All required files present")
        
        # Check CSV data
        try:
            import pandas as pd
            guest_df = pd.read_csv("Guest_profile_data.csv")
            room_df = pd.read_csv("Hotel_data_updated.csv")
            print(f"✅ Guest profiles: {len(guest_df)} records")
            print(f"✅ Hotel rooms: {len(room_df)} records")
        except Exception as e:
            print(f"⚠️  CSV files issue: {e}")
        
        return True
    
    def start_all_servers(self):
        """Start ALL servers including Context-Aware MCP server"""
        print("\n🚀 Starting Complete Context-Aware Hotel System...")
        
        # Start guest profile server (Port 8001)
        print("📊 Starting Guest Profile Server (Port 8001)...")
        self.guest_server = subprocess.Popen([
            sys.executable, "guest_profile_server.py"
        ])
        
        # Start booking server (Port 8002)
        print("🏨 Starting Booking Server (Port 8002)...")
        self.booking_server = subprocess.Popen([
            sys.executable, "booking_server.py"
        ])
        
        # UPDATED: Start Context-Aware MCP server (Port 8003)
        print("🧠 Starting Context-Aware Hotel MCP Server (Port 8003)...")
        self.context_mcp_server = subprocess.Popen([
            sys.executable, "hotel_mcp_sse_server.py"
        ])
        
        print("⏳ Waiting for all servers to initialize...")
        time.sleep(15)  # Give time for all servers to start
    
    async def test_server_connectivity(self):
        """Test if all servers are responding"""
        print("\n🔗 Testing Server Connectivity...")
        
        test_endpoints = {
            "Guest Profile Server": "http://localhost:8001/",
            "Booking Server": "http://localhost:8002/",
            "Context-Aware MCP Server": "http://localhost:8003/",  # UPDATED
            "Guest Data (Sample)": "http://localhost:8001/guest/by-id/1",
            "Room Data (Available)": "http://localhost:8002/rooms/available"
        }
        
        async with aiohttp.ClientSession() as session:
            all_connected = True
            
            for name, url in test_endpoints.items():
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            print(f"✅ {name}: Connected")
                            
                            # Show sample data for verification
                            if "guest/by-id/1" in url:
                                data = await response.json()
                                print(f"   Sample Guest: {data.get('first_name', 'N/A')} {data.get('last_name', 'N/A')}")
                            elif "rooms/available" in url:
                                data = await response.json()
                                print(f"   Available Rooms: {len(data)} rooms")
                            elif ":8003" in url:  # Context-aware server
                                data = await response.json()
                                transport = data.get('transport', 'unknown')
                                message = data.get('message', '')
                                print(f"   Transport: {transport}")
                                if "Context-Aware" in message:
                                    print(f"   🧠 AI Context Features: Active")
                        else:
                            print(f"❌ {name}: HTTP {response.status}")
                            all_connected = False
                            
                except asyncio.TimeoutError:
                    print(f"❌ {name}: Timeout - Server not responding")
                    all_connected = False
                except Exception as e:
                    print(f"❌ {name}: Failed - {str(e)}")
                    all_connected = False
            
            return all_connected
    
    def test_context_mcp_server_status(self):
        """Test Context-Aware MCP server status"""
        print("\n🧠 Testing Context-Aware MCP Server Status...")
        
        # Check if Context-Aware server process is running
        if self.context_mcp_server and self.context_mcp_server.poll() is None:
            print("✅ Context-Aware MCP Server Process: Running")
        else:
            print("❌ Context-Aware MCP Server Process: Not running or crashed")
            return False
        
        # Test Context-Aware endpoint availability
        try:
            response = requests.get("http://localhost:8003/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "Context-Aware" in data.get('message', ''):
                    print("✅ Context-Aware Features: Active")
                    print("✅ Deep Guest Analysis: Available")
                    print("✅ Autonomous Recommendations: Ready")
                    return True
                else:
                    print("❌ Context-Aware Features: Not configured properly")
                    return False
            else:
                print(f"❌ Context-Aware Server: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Context-Aware Server test failed: {e}")
            return False
    
    def test_context_components(self):
        """Test Context-Aware MCP components"""
        print("\n🧠 Checking Context-Aware Components...")
        
        # Check required packages
        try:
            import httpx
            print("✅ httpx package: Installed")
        except ImportError:
            print("❌ httpx package: Not installed - Run 'pip install httpx'")
        
        try:
            import requests
            print("✅ requests package: Installed")
        except ImportError:
            print("❌ requests package: Not installed - Run 'pip install requests'")
        
        try:
            import pandas as pd
            print("✅ pandas package: Installed")
        except ImportError:
            print("❌ pandas package: Not installed - Run 'pip install pandas'")
        
        # Check Context-Aware server file
        if os.path.exists("hotel_mcp_sse_server.py"):
            print("✅ Context-Aware MCP Server: hotel_mcp_sse_server.py found")
        else:
            print("❌ Context-Aware MCP Server: hotel_mcp_sse_server.py missing")
        
        # Check interface files with embedded clients
        if os.path.exists("guest_interface.py"):
            print("✅ Guest Interface (with embedded client): guest_interface.py found")
        else:
            print("❌ Guest Interface: guest_interface.py missing")
            
        if os.path.exists("staff_interface.py"):
            print("✅ Staff Interface (with embedded client): staff_interface.py found")
        else:
            print("❌ Staff Interface: staff_interface.py missing")
        
        print("ℹ️  Client agents are embedded in interface files (no separate client files needed)")
    
    def show_system_status(self):
        """Show complete system status and commands"""
        print("\n" + "="*70)
        print("🎉 CONTEXT-AWARE HOTEL MCP SYSTEM READY!")
        print("="*70)
        
        print("\n📊 RUNNING SERVERS:")
        print("   ✅ Guest Profile Server: http://localhost:8001")
        print("   ✅ Booking Server: http://localhost:8002")
        print("   ✅ Context-Aware Hotel MCP Server: http://localhost:8003")
        
        print("\n🧠 CONTEXT-AWARE FEATURES ACTIVE:")
        print("   🎯 Deep Guest Analysis (room_type, special_requests, amenities_used)")
        print("   🤖 Autonomous AI Recommendations (profession, loyalty, feedback-based)")
        print("   💡 Behavioral Pattern Recognition (satisfaction, spending, preferences)")
        print("   📊 Contextual Upselling & Intelligent Pricing")
        
        print("\n📱 STREAMLIT INTERFACES (with embedded clients):")
        print("   Run these commands in separate terminals:")
        print()
        print("   🌟 Context-Aware Guest Interface:")
        print("   streamlit run guest_interface.py --server.port 8501")
        print("   → Opens at: http://localhost:8501")
        print()
        print("   👨‍💼 Complete Staff Management Interface:")
        print("   streamlit run staff_interface.py --server.port 8502")
        print("   → Opens at: http://localhost:8502")
        
        print("\n💡 SYSTEM ARCHITECTURE:")
        print("   🔄 Guest/Staff UI (embedded clients) → Context-Aware MCP → FastAPI → CSV")
        print("   🧠 All operations enhanced with deep contextual analysis")
        print("   📊 Real-time sync with AI-powered guest insights")
        print("   🪟 Windows-compatible HTTP transport (no STDIO issues)")
        
        print("\n🎯 CONTEXTUAL FEATURES:")
        print("   • Complete guest profiles with behavioral analysis")
        print("   • Search guests by name or phone number")
        print("   • All rooms status (available + booked)")
        print("   • Autonomous AI recommendations engine")
        print("   • Context-aware booking with intelligent upselling")
        print("   • Deep satisfaction and loyalty predictions")
        
        print("\n⚠️  IMPORTANT:")
        print("   - Keep this terminal running for all servers")
        print("   - Context-Aware MCP provides AI-enhanced hotel operations")
        print("   - Guest profiles include deep contextual analysis")
        print("   - No separate client files needed (embedded in interfaces)")
    
    def cleanup_old_sessions(self):
        """Clean up old session files"""
        session_files = [
            "active_guest_sessions.json",
            "guest_recommendations.json"
        ]
        
        for file in session_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"🧹 Cleaned: {file}")
    
    def stop_all_servers(self):
        """Stop ALL running servers"""
        print("\n🛑 Stopping All Servers...")
        
        if self.guest_server:
            self.guest_server.terminate()
            print("✅ Guest Profile Server stopped")
        
        if self.booking_server:
            self.booking_server.terminate()
            print("✅ Booking Server stopped")
        
        if self.context_mcp_server:
            self.context_mcp_server.terminate()
            print("✅ Context-Aware MCP Server stopped")
        
        print("✅ Complete system shutdown")

async def main():
    """Main system startup orchestrator"""
    
    print("🧠" + "="*60)
    print("   CONTEXT-AWARE HOTEL MCP SYSTEM STARTUP")
    print("   Deep Guest Analysis • Autonomous AI • Windows Compatible")
    print("="*65)
    
    starter = ContextAwareHotelSystemStarter()
    
    # Step 1: Prerequisites check
    if not starter.check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix missing files.")
        return
    
    # Step 2: Clean old sessions
    starter.cleanup_old_sessions()
    
    # Step 3: Check Context-Aware components
    starter.test_context_components()
    
    # Step 4: Start ALL servers (including Context-Aware MCP)
    starter.start_all_servers()
    
    # Step 5: Test backend connectivity
    servers_ready = await starter.test_server_connectivity()
    
    # Step 6: Test Context-Aware MCP server status
    context_ready = starter.test_context_mcp_server_status()
    
    if servers_ready and context_ready:
        # Step 7: Show complete system status
        starter.show_system_status()
        
        print("\n" + "="*70)
        print("⏳ Complete Context-Aware system running...")
        print("🧠 AI-Enhanced hotel operations active")
        print("Press Ctrl+C to stop all servers")
        print("="*70)
        
        try:
            # Keep all servers running until user stops
            while True:
                await asyncio.sleep(1)
                
                # Check if any server crashed
                if (starter.guest_server and starter.guest_server.poll() is not None):
                    print("❌ Guest server crashed!")
                    break
                if (starter.booking_server and starter.booking_server.poll() is not None):
                    print("❌ Booking server crashed!")
                    break
                if (starter.context_mcp_server and starter.context_mcp_server.poll() is not None):
                    print("❌ Context-Aware MCP server crashed!")
                    break
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutdown signal received...")
    else:
        if not servers_ready:
            print("\n❌ Backend servers failed to start. Check error messages above.")
        if not context_ready:
            print("\n❌ Context-Aware MCP server failed to start. Check configuration.")
    
    # Cleanup
    starter.stop_all_servers()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ System stopped by user")
    except Exception as e:
        print(f"\n❌ System error: {e}")

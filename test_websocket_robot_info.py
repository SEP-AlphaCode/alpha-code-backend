"""
Test script cho Robot WebSocket Info Service
Test việc gửi command qua WebSocket để lấy thông tin robot
"""

import asyncio
import aiohttp
import json
import sys


async def test_websocket_robot_info(serial: str = "12345", server_url: str = "http://localhost:8000"):
    """
    Test việc lấy thông tin robot qua WebSocket
    
    Args:
        serial: Serial number của robot
        server_url: URL của server
    """
    print(f"🧪 Testing Robot WebSocket Info Service")
    print(f"📱 Serial: {serial}")
    print(f"🌐 Server: {server_url}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Kiểm tra robot có kết nối WebSocket không
        print("📡 Step 1: Checking WebSocket connections...")
        try:
            # Này chỉ là ví dụ - trong thực tế cần có endpoint để list connected robots
            # Hoặc có thể test trực tiếp bằng cách gửi command
            pass
        except Exception as e:
            print(f"❌ Error checking connections: {e}")
        
        # Test 2: Gửi command để lấy thông tin robot
        print("📤 Step 2: Sending info request via WebSocket...")
        try:
            url = f"{server_url}/robot/info/{serial}/websocket"
            params = {"timeout": 15}
            
            async with session.post(url, params=params) as response:
                status = response.status
                result = await response.json()
                
                print(f"📊 Status Code: {status}")
                print(f"📋 Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                if status == 200 and result.get('status') == 'success':
                    print("✅ WebSocket request successful!")
                    data = result.get('data', {})
                    print("\n🔍 Robot Info:")
                    print(f"  🔋 Battery: {data.get('battery_level', 'N/A')}%")
                    print(f"  💽 Firmware: {data.get('firmware_version', 'N/A')}")
                    print(f"  🎛️  Ctrl Version: {data.get('ctrl_version', 'N/A')}")
                    print(f"  🏷️  Serial: {data.get('serial_number', 'N/A')}")
                else:
                    print(f"❌ Request failed: {result.get('message', 'Unknown error')}")
                    
        except aiohttp.ClientError as e:
            print(f"❌ Network error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Test 3: Test với serial không tồn tại
        print(f"\n🧪 Step 3: Testing with non-existent serial...")
        try:
            fake_serial = "nonexistent123"
            url = f"{server_url}/robot/info/{fake_serial}/websocket"
            params = {"timeout": 5}
            
            async with session.post(url, params=params) as response:
                result = await response.json()
                print(f"📋 Result for non-existent robot: {result.get('message', 'No message')}")
                
        except Exception as e:
            print(f"❌ Error testing non-existent robot: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")


async def test_direct_websocket_command(serial: str = "12345", server_url: str = "http://localhost:8000"):
    """
    Test gửi command trực tiếp qua WebSocket endpoint
    """
    print(f"\n🔗 Testing direct WebSocket command...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Gửi command trực tiếp như trong websocket_router
            url = f"{server_url}/websocket/command/{serial}"
            command_data = {
                "type": "get_system_info",
                "data": {
                    "info_types": ["battery", "firmware", "ctrl_version", "serial"]
                }
            }
            
            async with session.post(url, json=command_data) as response:
                result = await response.json()
                print(f"📤 Direct command result: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"❌ Error sending direct command: {e}")


async def main():
    """Main test function"""
    print("🚀 Robot WebSocket Info Service Test Suite")
    
    # Get parameters from command line or input
    if len(sys.argv) > 1:
        serial = sys.argv[1]
    else:
        serial = input("Enter robot serial (or Enter for '12345'): ").strip()
        if not serial:
            serial = "12345"
    
    if len(sys.argv) > 2:
        server_url = sys.argv[2]
    else:
        server_url = "http://localhost:8000"
    
    print(f"Using serial: {serial}, server: {server_url}")
    print()
    
    # Run tests
    await test_websocket_robot_info(serial, server_url)
    await test_direct_websocket_command(serial, server_url)


if __name__ == "__main__":
    asyncio.run(main())

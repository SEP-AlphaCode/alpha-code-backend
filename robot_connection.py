"""
Robot Connection Module - Based on working UBtech example
Kết nối robot Alpha Mini sử dụng phương pháp đã test thành công
"""

import asyncio
import logging

# Apply websocket compatibility patch before importing Mini SDK
from websocket_patch import apply_websocket_patch
apply_websocket_patch()

import mini.mini_sdk as MiniSdk
from mini.dns.dns_browser import WiFiDevice


class RobotConnection:
    """Class quản lý kết nối robot Alpha Mini"""

    def __init__(self):
        self.device = None
        self.is_connected = False
        self.is_in_program_mode = False

        # Set log level and robot type như trong example thành công
        MiniSdk.set_log_level(logging.INFO)
        MiniSdk.set_robot_type(MiniSdk.RobotType.EDU)

    async def find_device_by_serial(self, serial_suffix="000341", timeout=10):
        """Tìm robot theo đuôi serial number"""
        try:
            result = await MiniSdk.get_device_by_name(serial_suffix, timeout)
            print(f"find_device_by_serial result: {result}")
            return result
        except Exception as e:
            print(f"Error finding device by serial: {e}")
            return None

    async def find_all_devices(self, timeout=10):
        """Tìm tất cả devices"""
        try:
            results = await MiniSdk.get_device_list(timeout)
            print(f"find_all_devices results = {results}")
            return results
        except Exception as e:
            print(f"Error finding devices: {e}")
            return []

    async def connect(self, device: WiFiDevice) -> bool:
        """Kết nối với device"""
        try:
            success = await MiniSdk.connect(device)
            if success:
                self.device = device
                self.is_connected = True
                print(f"Successfully connected to {device.name}")
            return success
        except Exception as e:
            print(f"Error connecting to device: {e}")
            return False

    async def enter_program_mode(self):
        """Vào chế độ programming"""
        try:
            await MiniSdk.enter_program()
            self.is_in_program_mode = True
            print("Entered programming mode successfully")
            # Wait for robot to finish announcement
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error entering program mode: {e}")
            raise

    async def disconnect(self):
        """Ngắt kết nối và giải phóng tài nguyên"""
        try:
            if self.is_in_program_mode:
                await MiniSdk.quit_program()
                self.is_in_program_mode = False

            if self.is_connected:
                await MiniSdk.release()
                self.is_connected = False
                self.device = None

            print("Robot disconnected successfully")
        except Exception as e:
            print(f"Error during disconnect: {e}")

    async def find_and_connect_auto(self, serial_suffix="000341"):
        """Tự động tìm và kết nối robot"""
        # Thử tìm theo serial trước
        device = await self.find_device_by_serial(serial_suffix)

        if not device:
            # Nếu không tìm thấy theo serial, tìm tất cả
            devices = await self.find_all_devices()
            if devices and len(devices) > 0:
                device = devices[0]

        if not device:
            print("No robot found")
            return False

        # Kết nối
        if await self.connect(device):
            print("Connection successful, entering program mode...")
            await asyncio.sleep(2)  # Wait for connection to stabilize
            await self.enter_program_mode()
            return True
        else:
            print("Failed to connect to device")
            return False


# Global instance
robot_connection = RobotConnection()


async def main():
    """Test connection"""
    try:
        success = await robot_connection.find_and_connect_auto()
        if success:
            print("Connection test completed successfully!")
            await asyncio.sleep(2)
            await robot_connection.disconnect()
        else:
            print("Connection test failed")
    except Exception as e:
        print(f"Error in main: {e}")


if __name__ == '__main__':
    asyncio.run(main())

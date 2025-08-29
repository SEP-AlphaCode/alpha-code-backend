import logging
from typing import Optional

# Apply websocket compatibility patch before importing Mini SDK
# import package-qualified so it works when running as part of the app package
from app.services.socket.websocket_patch import apply_websocket_patch
apply_websocket_patch()

import mini.mini_sdk as MiniSdk
from mini.dns.dns_browser import WiFiDevice


# To search for the robot with the specified serial number (behind the robot's butt), you can enter only the tail characters of the serial number, any length, it is recommended that more than 5 characters can be matched accurately, and the timeout is 10 seconds
# The search result WiFiDevice, contains robot name, ip, port and other information
async def test_get_device_by_name(serial_tail: str, timeout: int = 10) -> Optional[WiFiDevice]:
    """Search for devices based on the suffix of the robot serial number

     To search for the robot with the specified serial number (behind the robot's butt), you can enter only the tail characters of the serial number, any length, it is recommended that more than 5 characters can be matched accurately, and a timeout of 10 seconds


     Returns:
         WiFiDevice: Contains information such as robot name, ip, port, etc. Or None when not found.
    """
    result: WiFiDevice = await MiniSdk.get_device_by_name(serial_tail, timeout)
    print(f"test_get_device_by_name('{serial_tail}') result:{result}")
    return result


async def connect_by_serial(serial_tail: str, timeout: int = 10) -> Optional[WiFiDevice]:
    """Find device by serial tail and connect to it. Returns the connected WiFiDevice or None on failure."""
    device = await test_get_device_by_name(serial_tail, timeout)
    if not device:
        print(f"No device found for serial: {serial_tail}")
        return None

    connected = await MiniSdk.connect(device)
    if connected:
        print(f"Connected to device {device}")
        return device
    else:
        print(f"Failed to connect to device {device}")
        return None


# Enter the programming mode, the robot has a tts broadcast, here through asyncio.sleep, let the current coroutine wait 6 seconds to return, let the robot finish the broadcast
async def test_start_run_program():
    """Enter programming mode demo

     Make the robot enter the programming mode, wait for the reply result, and delay 6 seconds, let the robot finish "Enter programming mode"

     Returns:
         None:

    """
    await MiniSdk.enter_program()


# Disconnect and release resources
async def shutdown():
    """Disconnect and release resources

     Disconnect the currently connected device and release resources

    """
    await MiniSdk.quit_program()
    await MiniSdk.release()


# The default log level is Warning, set to INFO
MiniSdk.set_log_level(logging.INFO)
# Set robot type
MiniSdk.set_robot_type(MiniSdk.RobotType.EDU)


# Note: module no longer runs standalone. Import its functions from routers or services.

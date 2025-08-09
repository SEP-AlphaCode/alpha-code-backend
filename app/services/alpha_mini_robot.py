"""
Alpha Mini Robot Service
Service để điều khiển robot Alpha Mini của UBtech
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from mini.apis.api_behavior import StartBehavior, StopBehavior, ControlBehaviorResponse
from mini.apis.api_expression import PlayExpression, PlayExpressionResponse
from mini.apis.api_sound import StartPlayTTS, StopPlayTTS, ControlTTSResponse
from mini.apis.base_api import MiniApiResultType
from mini.dns.dns_browser import WiFiDevice
import mini.mini_sdk as MiniSdk
# NEW: Use PlayAction for non-dance actions
from mini.apis.api_action import PlayAction, PlayActionResponse
# NEW: Probe available actions
from mini.apis.api_action import GetActionList, GetActionListResponse, RobotActionType

# Try to import lamp APIs - these might have different names in different SDK versions
try:
    from mini.apis.api_lamp import SetMouthLamp, ControlMouthLamp, SetMouthLampResponse, ControlMouthResponse
    from mini.apis.api_lamp import MouthLampColor, MouthLampMode
    LAMP_API_AVAILABLE = True
except ImportError:
    try:
        from mini.apis.api_mouth import SetMouthLamp, ControlMouthLamp, SetMouthLampResponse, ControlMouthResponse  
        from mini.apis.api_mouth import MouthLampColor, MouthLampMode
        LAMP_API_AVAILABLE = True
    except ImportError:
        print("⚠️ Warning: Mouth lamp APIs not available in this SDK version")
        LAMP_API_AVAILABLE = False
        # Define dummy classes to avoid errors
        class MouthLampColor:
            RED = 1
            GREEN = 2 
            BLUE = 3
        class MouthLampMode:
            NORMAL = 0
            BREATH = 1

# Import websocket patch
from websocket_patch import apply_websocket_patch
apply_websocket_patch()

logger = logging.getLogger(__name__)

class AlphaMiniRobotService:
    """Service để điều khiển robot Alpha Mini"""

    def __init__(self):
        self.device: Optional[WiFiDevice] = None
        self.is_connected = False
        self.is_in_program_mode = False
        self.current_music_task = None
        self.current_dance_task = None
        self.current_lamp_task = None
        # NEW: cache available action files and serialize motions
        self.available_action_files: set[str] = set()
        self.motion_lock = asyncio.Lock()

        # Setup SDK như trong example thành công
        MiniSdk.set_log_level(logging.INFO)
        MiniSdk.set_robot_type(MiniSdk.RobotType.EDU)

    async def find_and_connect(self, device_serial: str = "000341") -> bool:
        """Tìm và kết nối robot sử dụng phương pháp từ UBtech SDK đã test thành công"""
        try:
            print(f"Searching for robot with serial ending: {device_serial}")

            # Tìm theo serial number (chỉ cần đuôi serial)
            self.device = await MiniSdk.get_device_by_name(device_serial, 10)
            print(f"Device search result: {self.device}")

            if not self.device:
                # Thử tìm tất cả devices
                print("Searching for all available robots...")
                devices = await MiniSdk.get_device_list(10)
                print(f"All devices found: {devices}")

                if devices and len(devices) > 0:
                    self.device = devices[0] if isinstance(devices, (list, tuple)) else None

            if not self.device:
                logger.error("❌ No robot found")
                return False

            # Kết nối như trong example
            print(f"Connecting to robot: {self.device.name}")
            connected = await MiniSdk.connect(self.device)

            if connected:
                self.is_connected = True
                print("Connection successful")

                # Vào chế độ programming
                print("Entering programming mode...")
                await asyncio.sleep(2)  # Wait for connection to stabilize
                await MiniSdk.enter_program()
                self.is_in_program_mode = True
                print("Programming mode activated")

                # NEW: Refresh available action files list
                try:
                    await self.refresh_available_actions()
                except Exception as refresh_err:
                    print(f"Failed to refresh available actions: {refresh_err}")

                return True
            else:
                logger.error("❌ Failed to connect to robot")
                return False

        except Exception as e:
            logger.error(f"❌ Error connecting to robot: {e}")
            return False

    async def refresh_available_actions(self) -> None:
        """Lấy danh sách action file (INNER + CUSTOM) và cache lại"""
        names: set[str] = set()
        # INNER
        rt1, resp1 = await GetActionList(action_type=RobotActionType.INNER).execute()
        if rt1 == MiniApiResultType.Success and isinstance(resp1, GetActionListResponse) and resp1.isSuccess:
            for item in (resp1.actions or []):
                # item likely has name or actionName
                nm = getattr(item, 'name', None) or getattr(item, 'actionName', None)
                if nm:
                    names.add(nm)
        # CUSTOM
        rt2, resp2 = await GetActionList(action_type=RobotActionType.CUSTOM).execute()
        if rt2 == MiniApiResultType.Success and isinstance(resp2, GetActionListResponse) and resp2.isSuccess:
            for item in (resp2.actions or []):
                nm = getattr(item, 'name', None) or getattr(item, 'actionName', None)
                if nm:
                    names.add(nm)
        self.available_action_files = names
        print(f"Cached {len(self.available_action_files)} available action files")

    def is_action_file(self, name: str) -> bool:
        """Heuristic: action file names look like 'action_XXX' or purely digits."""
        return name.startswith("action_") or name.isdigit()

    def is_available_action(self, name: str) -> bool:
        if not self.available_action_files:
            return True  # no info; allow
        return name in self.available_action_files

    async def disconnect(self):
        """Ngắt kết nối robot"""
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
            logger.error(f"Error disconnecting robot: {e}")

    async def execute_action(self, action_name: str, duration: float = 2.0) -> bool:
        """Thực hiện action trên robot
        - Dance (tên bắt đầu bằng 'dance_'): StartBehavior
        - Action file (action_XXX hoặc số): PlayAction
        - Behavior khác (vd: w_stand_0009): StartBehavior
        Serialize để tránh chồng chéo.
        """
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            async with self.motion_lock:
                # DANCE
                if action_name.startswith("dance_"):
                    print(f"Executing dance: {action_name}")
                    block = StartBehavior(name=action_name)
                    result_type, response = await block.execute()

                    if (result_type == MiniApiResultType.Success and
                        response and response.isSuccess):
                        print(f"Dance {action_name} started successfully")
                        await asyncio.sleep(min(duration, 10.0))
                        try:
                            await StopBehavior().execute()
                            print(f"Dance {action_name} stopped")
                        except:
                            pass
                        return True
                    else:
                        print(f"Dance {action_name} failed: {response.resultCode if response else 'No response'}")
                        return False

                # ACTION FILE via PlayAction
                if self.is_action_file(action_name):
                    print(f"Executing action file (PlayAction): {action_name}")
                    variants = {action_name}
                    if action_name.startswith("action_") and action_name[7:].isdigit():
                        num = action_name[7:]
                        variants.add(num)
                    if action_name.isdigit():
                        variants.add(f"action_{action_name}")

                    # Prefer a variant that exists on device if we know the list
                    ordered_variants = sorted(list(variants), key=lambda v: (0 if self.is_available_action(v) else 1, len(v)))

                    for variant in ordered_variants:
                        try:
                            block = PlayAction(action_name=variant)
                            result_type, response = await block.execute()
                            if (result_type == MiniApiResultType.Success and response and getattr(response, 'isSuccess', False)):
                                print(f"Action {variant} played successfully")
                                return True
                            else:
                                code = getattr(response, 'resultCode', 'No response') if response else 'No response'
                                print(f"Action {variant} failed: {code}")
                        except Exception as action_error:
                            print(f"Failed to play action {variant}: {action_error}")
                            continue
                    return False

                # OTHER BEHAVIOR via StartBehavior
                print(f"Executing behavior: {action_name}")
                try:
                    block = StartBehavior(name=action_name)
                    result_type, response = await block.execute()
                    if (result_type == MiniApiResultType.Success and response and response.isSuccess):
                        print(f"Behavior {action_name} executed successfully")
                        await asyncio.sleep(min(duration, 3.0))
                        return True
                    else:
                        print(f"Behavior {action_name} failed: {response.resultCode if response else 'No response'}")
                        return False
                except Exception as e:
                    print(f"Failed to execute behavior {action_name}: {e}")
                    return False

        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            return False

    async def play_expression(self, expression_name: str) -> bool:
        """Phát expression trên robot, serialize để tránh chồng nhau với action"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            base_name = expression_name[:-4] if expression_name.endswith('.ubx') else expression_name
            expression_variants = [base_name]

            async with self.motion_lock:
                for variant in expression_variants:
                    try:
                        print(f"Playing expression: {variant}")
                        block = PlayExpression(express_name=variant)
                        result_type, response = await block.execute()

                        if (result_type == MiniApiResultType.Success and
                            response and response.isSuccess):
                            print(f"Expression {variant} played successfully")
                            return True
                        else:
                            print(f"Expression {variant} failed: {response.resultCode if response else 'No response'}")

                    except Exception as expr_error:
                        print(f"Failed to play {variant}: {expr_error}")
                        continue

            return False

        except Exception as e:
            logger.error(f"Error playing expression {expression_name}: {e}")
            return False

    async def speak_text(self, text: str) -> bool:
        """Robot nói text"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            block = StartPlayTTS(text=text)
            result_type, response = await block.execute()

            if result_type == MiniApiResultType.Success and response and response.isSuccess:
                print(f"Robot spoke: {text}")
                return True
            else:
                print(f"Failed to speak text: {response.resultCode if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False

    async def stop_current_action(self):
        """Dừng action hiện tại"""
        try:
            if self.is_connected and self.is_in_program_mode:
                block = StopBehavior()
                await block.execute()
                print("Stopped current action")
        except Exception as e:
            logger.error(f"Error stopping action: {e}")

    async def set_mouth_lamp(self, color: str, mode: str = "normal", duration: int = 3000, breath_duration: int = 1000) -> bool:
        """Đặt màu và chế độ đèn miệng"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        if not LAMP_API_AVAILABLE:
            print("Mouth lamp API not available, simulating...")
            return True

        try:
            # Map color names to values
            color_map = {
                "red": 1, "green": 2, "blue": 3
            }
            
            # Map mode names to values  
            mode_map = {"normal": 0, "breath": 1}
            
            color_value = color_map.get(color.lower(), 2)  # Default to green
            mode_value = mode_map.get(mode.lower(), 0)     # Default to normal
            
            print(f"Setting mouth lamp: {color}, mode: {mode}")
            
            # Try different API approaches
            try:                
                # Map our values to the enum values
                if color_value == 1:
                    lamp_color = MouthLampColor.RED
                elif color_value == 2:
                    lamp_color = MouthLampColor.GREEN  
                elif color_value == 3:
                    lamp_color = MouthLampColor.BLUE

                block: SetMouthLamp = SetMouthLamp(lamp_color=lamp_color, mode=MouthLampMode.NORMAL,
                                       duration=3000, breath_duration=1000)
    # response:SetMouthLampResponse
                (resultType, response) = await block.execute()
                
                assert resultType == MiniApiResultType.Success, 'test_set_mouth_lamp timetout'
                assert response is not None and isinstance(response, SetMouthLampResponse), 'test_set_mouth_lamp result unavailable'
                assert response.isSuccess or response.resultCode == 504, 'set_mouth_lamp failed'
                    
            except ImportError:
                # Fallback: Try using behavior system to control lights
                print("Using behavior fallback for mouth lamp")
                light_behavior_name = f"light_{color}_{mode}"
                return await self.execute_action(light_behavior_name, 1.0)
                
        except Exception as e:
            logger.error(f"Error setting mouth lamp: {e}")
            return False

    async def control_mouth_lamp(self, is_open: bool) -> bool:
        """Bật/tắt đèn miệng"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        if not LAMP_API_AVAILABLE:
            print("Mouth lamp API not available, simulating...")
            return True

        try:
            print(f"{'Opening' if is_open else 'Closing'} mouth lamp")
            
            try:
                from mini.apis.api_lamp import ControlMouthLamp
                
                result_type, response = await ControlMouthLamp(is_open=is_open).execute()
                
                if result_type == MiniApiResultType.Success and response and (response.isSuccess or response.resultCode == 504):
                    print(f"Mouth lamp {'opened' if is_open else 'closed'} successfully")
                    return True
                else:
                    print(f"Failed to control mouth lamp: {response.resultCode if response else 'No response'}")
                    return False
                    
            except ImportError:
                # Fallback
                return await self.set_mouth_lamp("white" if is_open else "off")
                
        except Exception as e:
            logger.error(f"Error controlling mouth lamp: {e}")
            return False

    async def start_dance_behavior(self, dance_name: str) -> bool:
        """Bắt đầu một dance behavior (không đợi kết thúc)"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            print(f"Starting dance behavior: {dance_name}")
            block = StartBehavior(name=dance_name)
            result_type, response = await block.execute()

            if result_type == MiniApiResultType.Success and response and response.isSuccess:
                print(f"Dance behavior {dance_name} started successfully")
                return True
            else:
                print(f"Failed to start dance behavior: {response.resultCode if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"Error starting dance behavior: {e}")
            return False

    async def stop_behavior(self) -> bool:
        """Dừng behavior hiện tại"""
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            print("Stopping current behavior")
            block = StopBehavior()
            result_type, response = await block.execute()

            if result_type == MiniApiResultType.Success:
                print("Behavior stopped successfully")
                return True
            else:
                print(f"Failed to stop behavior: {response.resultCode if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"Error stopping behavior: {e}")
            return False

    async def continuous_dance_with_expressions_and_lights(
        self, 
        dance_sequence: List[str], 
        expressions: List[str],
        light_colors: List[str],
        segment_duration: float = 6.0
    ) -> bool:
        """
        Thực hiện choreography liên tục với dance, expressions và lights
        """
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            print("Starting continuous dance with expressions and lights...")
            
            total_segments = max(len(dance_sequence), len(expressions), len(light_colors))
            
            for i in range(total_segments):
                segment_start_time = asyncio.get_event_loop().time()
                
                # Get current segment items (cycle through if lists are different lengths)
                current_dance = dance_sequence[i % len(dance_sequence)] if dance_sequence else None
                current_expression = expressions[i % len(expressions)] if expressions else None  
                current_color = light_colors[i % len(light_colors)] if light_colors else "green"
                
                print(f"Segment {i+1}: Dance={current_dance}, Expression={current_expression}, Light={current_color}")
                
                # Start tasks simultaneously
                tasks = []
                
                # 1. Start dance behavior
                if current_dance:
                    tasks.append(asyncio.create_task(self.start_dance_behavior(current_dance)))
                
                # 2. Set mouth light color
                if current_color:
                    tasks.append(asyncio.create_task(self.set_mouth_lamp(
                        current_color, "breath", duration=int(segment_duration * 1000), breath_duration=500
                    )))
                
                # Wait a bit then add expression
                await asyncio.sleep(0.5)
                
                # 3. Play expression
                if current_expression:
                    tasks.append(asyncio.create_task(self.play_expression(current_expression)))
                
                # Wait for initial tasks to start
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait for segment duration
                elapsed = asyncio.get_event_loop().time() - segment_start_time
                remaining = segment_duration - elapsed
                
                if remaining > 0:
                    await asyncio.sleep(remaining)
                
                # Stop current behavior before next segment
                await self.stop_behavior()
                await asyncio.sleep(0.2)  # Brief pause between segments
            
            print("Continuous dance sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"Error in continuous dance: {e}")
            # Ensure we stop any running behaviors
            try:
                await self.stop_behavior()
            except:
                pass
            return False

    async def play_dance(self, dance_name: str, duration: float = None) -> bool:
        """Enhanced play dance method"""
        return await self.execute_action(dance_name, duration or 10.0)

    async def play_action(self, action_name: str, duration: float = None) -> bool:
        """Enhanced play action method"""  
        return await self.execute_action(action_name, duration or 3.0)

    async def synchronized_performance(
        self,
        actions: List[Dict[str, Any]],
        total_duration: float
    ) -> bool:
        """
        Thực hiện performance đồng bộ với nhiều loại actions
        actions format: [{"type": "dance/action/expression/light", "name": "...", "start_time": 0.0, "duration": 2.0, "params": {}}]
        - Bỏ qua các action bị trễ quá ngưỡng (giảm hiện tượng delay/catch-up)
        - Không khởi động action mới khi gần hết bài (tránh chạy quá thời lượng nhạc)
        - Khi kết thúc, dừng behavior và huỷ các task còn chạy (đèn, nói)
        """
        if not self.is_connected or not self.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            print(f"Starting synchronized performance ({total_duration}s)")
            late_tolerance = 0.35   # giây: nếu trễ hơn ngưỡng này thì bỏ qua action đó
            min_start_window = 0.6  # giây: không khởi động action mới nếu còn ít hơn vậy
            min_expr_window = 0.5
            min_light_window = 0.2

            start_time = asyncio.get_event_loop().time()
            running_tasks = []

            # Sort actions by start time
            sorted_actions = sorted(actions, key=lambda x: x.get("start_time", 0))
            action_index = 0

            while action_index < len(sorted_actions):
                now = asyncio.get_event_loop().time()
                current_time = now - start_time
                remaining_total = total_duration - current_time

                # Stop scheduling if we're basically at the end
                if remaining_total <= 0.05:
                    break

                # Start all actions that should start at this time
                while action_index < len(sorted_actions):
                    action = sorted_actions[action_index]
                    sched = float(action.get("start_time", 0.0))
                    action_type = action.get("type", "action")
                    action_name = action.get("name", "")
                    action_duration = float(action.get("duration", 2.0))
                    action_params = action.get("params", {})

                    # Only start when it's time; if not yet, break inner loop
                    if sched > current_time:
                        break

                    # Drop actions that are too late
                    if current_time - sched > late_tolerance:
                        print(f"Skip late {action_type}: {action_name} (late {current_time - sched:.2f}s)")
                        action_index += 1
                        continue

                    # Don't start if not enough time remaining
                    if action_type in ("dance", "action", "expression") and remaining_total < min_start_window:
                        print(f"Skip near-end {action_type}: {action_name} (remaining {remaining_total:.2f}s)")
                        action_index += 1
                        continue
                    if action_type == "light" and remaining_total < min_light_window:
                        print(f"Skip near-end light: {action_name}")
                        action_index += 1
                        continue

                    print(f"Starting {action_type}: {action_name} at {current_time:.1f}s")

                    # Create appropriate task based on action type
                    if action_type == "dance":
                        # Ensure previous behavior is stopped so the new dance starts cleanly
                        try:
                            await self.stop_behavior()
                        except Exception:
                            pass
                        await self.start_dance_behavior(action_name)
                    elif action_type == "action":
                        await self.execute_action(action_name, action_duration)
                    elif action_type == "expression":
                        # Only if enough expr window remains
                        if remaining_total >= min_expr_window:
                            await self.play_expression(action_name)
                    elif action_type == "light":
                        color = action_params.get("color", "green")
                        mode = action_params.get("mode", "normal")
                        task = asyncio.create_task(self.set_mouth_lamp(color, mode, int(min(action_duration, remaining_total) * 1000)))
                        running_tasks.append({"task": task, "end_time": current_time + action_duration, "type": action_type, "name": action_name})
                    else:
                        print(f"⚠️ Unknown action type: {action_type}")
                        action_index += 1
                        continue

                    action_index += 1

                # Clean up completed tasks
                running_tasks = [t for t in running_tasks if not t["task"].done()]

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.03)

            # Music ended or schedule finished: stop everything immediately
            print("Stopping performance at music end")
            # Cancel any pending aux tasks
            for t in running_tasks:
                if not t["task"].done():
                    t["task"].cancel()
                    try:
                        await t["task"]
                    except Exception:
                        pass
            # Stop current behavior (dances)
            await self.stop_behavior()

            print("Synchronized performance completed")
            return True
            
        except Exception as e:
            logger.error(f"Error in synchronized performance: {e}")
            try:
                await self.stop_behavior()
            except:
                pass
            return False

# Global instance
alpha_mini_robot_service = AlphaMiniRobotService()

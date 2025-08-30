from typing import Any, Dict

from app.utils.error_utils import get_express_error_str
from mini import MiniApiResultType
from mini.apis.api_behavior import StartBehavior
from mini.pb2.codemao_controlbehavior_pb2 import ControlBehaviorResponse


async def action_behavior(action_code: str):
    """Test action execution

     Let the robot start an action (for example "action_0004") and wait for the response result

    """
    # control_type: START, STOP
    block: StartBehavior = StartBehavior(name=action_code)
    # response ControlBehaviorResponse
    (resultType, response) = await block.execute()

    print(f'test_control_behavior result: {response}')
    print(
        f'resultCode = {response.resultCode}, error = {get_express_error_str(response.resultCode)}'
    )

    assert resultType == MiniApiResultType.Success, 'test_control_behavior timetout'
    assert response is not None and isinstance(response,
                                               ControlBehaviorResponse), 'test_control_behavior result unavailable'
    assert response.isSuccess, 'control_behavior failed'


async def run_actions_for_serial(serial: str, code: str, timeout: int = 10) -> Dict[str, Any]:
    """Connect to robot by serial tail, run a set of actions, and ensure cleanup.

    Returns a dict with per-action results and an overall status.
    """
    results: Dict[str, Any] = {
        "connected": False,
        "play_action": None,
        "move_robot": None,
        "get_action_list": None,
        "error": None,
    }

    # Use package-qualified import so the module is found when running under the app package
    from app.services.robot_sdk_control.connect_service import connect_by_serial, shutdown

    try:
        device = await connect_by_serial(serial, timeout=timeout)
        if not device:
            results["error"] = f"device_not_found_or_connect_failed:{serial}"
            return results
        results["connected"] = True

        try:
            play_resp = await action_behavior(code)
            results["play_action"] = repr(play_resp)
        except Exception as e:
            results["play_action"] = {"error": str(e)}

        # try:
        #     move_resp = await test_move_robot()
        #     results["move_robot"] = repr(move_resp)
        # except Exception as e:
        #     results["move_robot"] = {"error": str(e)}
        #
    # try:
    #     list_resp = await test_get_action_list()
    #     results["get_action_list"] = repr(list_resp)
    # except Exception as e:
    #     results["get_action_list"] = {"error": str(e)}

        return results

    except Exception as e:
        results["error"] = f"unexpected_error:{e}"
        return results

    finally:
        try:
            await shutdown()
        except Exception as e:
            print(f"Error during shutdown: {e}")


from idlelib.iomenu import errors
from typing import Any, Dict

from mini import MiniApiResultType
from mini.apis.api_behavior import StartBehavior
from mini.pb2.codemao_controlbehavior_pb2 import ControlBehaviorResponse


async def dances_behavior(dance_code: str):
    """Test dances performance

     Let the robot start a dances named "dance_0004" and wait for the response result

    """
    # control_type: START, STOP
    block: StartBehavior = StartBehavior(name=dance_code)
    # response ControlBehaviorResponse
    (resultType, response) = await block.execute()

    print(f'test_control_behavior result: {response}')
    print(
        'resultCode = {0}, error = {1}'.format(response.resultCode, errors.get_express_error_str(response.resultCode)))

    assert resultType == MiniApiResultType.Success, 'test_control_behavior timetout'
    assert response is not None and isinstance(response,
                                               ControlBehaviorResponse), 'test_control_behavior result unavailable'
    assert response.isSuccess, 'control_behavior failed'


async def run_dances_for_serial(serial: str,code: str,timeout: int = 10) -> Dict[str, Any]:
    """Connect to robot by serial tail, run a set of dances, and ensure cleanup.

    Returns a dict with per-dances results and an overall status.
    """
    results: Dict[str, Any] = {
        "connected": False,
        "play_dance": None,
        "move_robot": None,
        "get_dance_list": None,
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
            play_resp = await dances_behavior(code)
            results["play_dance"] = repr(play_resp)
        except Exception as e:
            results["play_dance"] = {"error": str(e)}

        # try:
        #     move_resp = await test_move_robot()
        #     results["move_robot"] = repr(move_resp)
        # except Exception as e:
        #     results["move_robot"] = {"error": str(e)}
        #
        # try:
        #     list_resp = await test_get_dance_list()
        #     results["get_dance_list"] = repr(list_resp)
        # except Exception as e:
        #     results["get_dance_list"] = {"error": str(e)}

        return results

    except Exception as e:
        results["error"] = f"unexpected_error:{e}"
        return results

    finally:
        try:
            await shutdown()
        except Exception as e:
            print(f"Error during shutdown: {e}")


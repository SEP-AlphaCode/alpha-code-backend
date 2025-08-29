import asyncio
from typing import Any, Dict

from mini.apis.api_action import GetActionList, GetActionListResponse, RobotActionType
from mini.apis.api_action import MoveRobot, MoveRobotDirection, MoveRobotResponse
from mini.apis.api_action import PlayAction, PlayActionResponse
from mini.apis.base_api import MiniApiResultType


async def play_action(action_code: str) -> PlayActionResponse:
    """Perform an action demo

     Control the robot to execute a local (built-in/custom) action with a specified name and wait for the execution result to reply

     Action name can be obtained with GetActionList

     #PlayActionResponse.isSuccess: Is it successful

     #PlayActionResponse.resultCode: Return code

     """
    # action_name: Action file name, you can get the actions supported by the robot through GetActionList
    block: PlayAction = PlayAction(action_name=action_code)
    # response: PlayActionResponse
    (resultType, response) = await block.execute()

    print(f'play_action result:{response}')

    if resultType != MiniApiResultType.Success or response is None or not isinstance(response, PlayActionResponse) or not response.isSuccess:
        raise RuntimeError('play_action failed')

    return response


async def test_move_robot() -> MoveRobotResponse:
    """Control the robot mobile demo

     Control the robot to move 10 steps to the left (LEFTWARD) and wait for the execution result

     #MoveRobotResponse.isSuccess: Is it successful　

     #MoveRobotResponse.code: Return code

     """
    # step: Move a few steps
    # direction: direction, enumeration type
    block: MoveRobot = MoveRobot(step=10, direction=MoveRobotDirection.LEFTWARD)
    # response : MoveRobotResponse
    (resultType, response) = await block.execute()

    print(f'test_move_robot result:{response}')

    if resultType != MiniApiResultType.Success or response is None or not isinstance(response, MoveRobotResponse) or not response.isSuccess:
        raise RuntimeError('test_move_robot failed')

    return response


# 测试, 获取支持的动作文件列表
async def test_get_action_list() -> GetActionListResponse:
    """Get action list demo

     Get the list of built-in actions of the robot and wait for the reply result

    """
    # action_type: INNER refers to the unmodifiable action file built into the robot, and CUSTOM is an action that can be modified by the developer placed in the sdcard/customize/action directory
    block: GetActionList = GetActionList(action_type=RobotActionType.INNER)
    # response:GetActionListResponse
    (resultType, response) = await block.execute()

    print(f'test_get_action_list result:{response}')

    if resultType != MiniApiResultType.Success or response is None or not isinstance(response, GetActionListResponse) or not response.isSuccess:
        raise RuntimeError('test_get_action_list failed')

    return response


async def run_actions_for_serial(serial: str,code: str,timeout: int = 10) -> Dict[str, Any]:
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
            play_resp = await play_action(code)
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


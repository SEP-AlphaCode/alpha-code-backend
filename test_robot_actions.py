import asyncio
import argparse
import sys

from app.services.alpha_mini_robot import alpha_mini_robot_service


async def main():
    parser = argparse.ArgumentParser(description="Quick test for Alpha Mini actions/dances")
    parser.add_argument("--serial", default="000341", help="Tail of robot serial to connect")
    parser.add_argument("--action", default="action_013", help="Action name to play via PlayAction")
    parser.add_argument("--dance", default=None, help="Dance name to run via StartBehavior (optional)")
    parser.add_argument("--dance-duration", type=float, default=6.0, help="Dance duration seconds before stopping")
    args = parser.parse_args()

    print(f"Connecting to robot (serial endswith {args.serial})...")
    connected = await alpha_mini_robot_service.find_and_connect(args.serial)
    if not connected:
        print("Failed to connect to robot")
        sys.exit(1)

    ok = True

    if args.action:
        print(f"\n--- Testing Action (PlayAction): {args.action} ---")
        res = await alpha_mini_robot_service.play_action(args.action)
        print(f"Action result: {'OK' if res else 'FAIL'}")
        ok = ok and res

    if args.dance:
        print(f"\n--- Testing Dance (StartBehavior): {args.dance} ---")
        res = await alpha_mini_robot_service.play_dance(args.dance, duration=args.dance_duration)
        print(f"Dance result: {'OK' if res else 'FAIL'}")
        ok = ok and res

    await alpha_mini_robot_service.disconnect()

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())

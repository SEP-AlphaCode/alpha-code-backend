async def handle_binary_message(data: bytes, serial: str) -> None:
    try:
        print(data)
        return
    except UnicodeDecodeError as ue:
        print('Decode error', ue)

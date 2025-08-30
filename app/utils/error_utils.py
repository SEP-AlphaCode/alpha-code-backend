def get_express_error_str(code: int) -> str:
    error_map = {
        0: "Success",
        1: "Timeout",
        2: "InvalidParameter",
        3: "ConnectionFailed",
    }
    return error_map.get(code, f"UnknownError({code})")
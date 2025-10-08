from app.models.proto.robot_command_pb2 import RobotRequest
from app.models.stt import ASRData
from app.services.socket.handlers.command_handler import process_speech, detect_object, parse_osmo, notify_shutdown


async def handle_command(req: RobotRequest):
    try:
        command_type = req.type
        print(command_type)
        if command_type == "process-speech":
            # Convert asr bytes to ASRData object
            asr_data = ASRData(arr=list(req.asr))
            return await process_speech(asr_data)
        
        elif command_type == "detect-object":
            return await detect_object(req.image)
        
        elif command_type == "parse-osmo":
            return await parse_osmo(req.image)
        
        elif command_type == 'notify-shutdown':
            serial = req.params['serial']
            return await notify_shutdown(serial)
        else:
            return {"error": f"Unknown command type: {command_type}"}
    
    except Exception as e:
        return {"error": str(e)}
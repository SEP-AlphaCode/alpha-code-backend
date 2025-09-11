# Robot Info Service

Service để lấy thông tin cơ bản từ robot Alpha Mini qua WebSocket command.

## Thông tin lấy được

Service sẽ trả về 4 thông tin cơ bản:

1. **battery_level** - Mức pin (%)
2. **firmware_version** - Phiên bản firmware  
3. **ctrl_version** - Phiên bản control
4. **serial_number** - Serial number của robot

## API Endpoint

### POST /robot/info/{serial}

Gửi lệnh qua WebSocket đến robot đã kết nối để lấy thông tin.

**Parameters:**
- `serial` (path): Serial number của robot đã kết nối WebSocket
- `timeout` (query): Timeout chờ response từ robot (1-30 giây, mặc định 10)

**Response:**
```json
{
  "status": "success",
  "message": "Robot info retrieved successfully via WebSocket",
  "data": {
    "battery_level": 85,
    "firmware_version": "v2.1.0",
    "ctrl_version": "v1.5.2", 
    "serial_number": "AM123456789"
  }
}
```

**Ví dụ sử dụng:**
```bash
curl -X POST "http://localhost:8000/robot/info/12345?timeout=10"
```

**Lưu ý:** Robot phải đã kết nối WebSocket trước khi sử dụng endpoint này.

## Test Script

```bash
# Test WebSocket command (cần cài aiohttp: pip install aiohttp)
python test_robot_info.py

# Test với serial và server cụ thể  
python test_robot_info.py AM12345 http://localhost:8000
```

## Cách hoạt động

1. Robot kết nối WebSocket với server qua `/ws/{serial}`
2. Server gửi command qua WebSocket:
   ```json
   {
     "type": "get_system_info",
     "request_id": "info_req_xxx",
     "data": {
       "info_types": ["battery", "firmware", "ctrl_version", "serial"]
     }
   }
   ```
3. Robot trả về response:
   ```json
   {
     "type": "system_info_response", 
     "request_id": "info_req_xxx",
     "data": {
       "battery_level": 85,
       "firmware_version": "v2.1.0",
       "ctrl_version": "v1.5.2", 
       "serial_number": "AM123456789"
     }
   }
   ```
4. Server parse và trả về cho client

## Lưu ý

- Robot phải đã kết nối WebSocket với server trước khi gọi API
- Timeout ngắn (1-30s) vì robot đã kết nối sẵn
- Nếu robot không phản hồi trong thời gian timeout, sẽ trả về error

## Error Handling

- **400**: Serial number không hợp lệ, timeout không đúng, hoặc robot không phản hồi
- **500**: Lỗi server hoặc lỗi xử lý WebSocket

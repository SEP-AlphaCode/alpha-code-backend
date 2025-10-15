# Alpha Mini Robot API

This project is a FastAPI backend for controlling and interacting with the Alpha Mini robot, including features for Osmo
coding card recognition and audio conversion.

## Project Structure

- `main.py`: Entry point, includes FastAPI app and router registration.
- `routers/`: Contains API route definitions.
- `models/`: Pydantic models for request/response schemas.
- `services/`: Business logic and robot control functions.
- `utils/`: Utility/helper functions.

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install system dependencies

#### **FFmpeg** (for audio conversion)

- **Windows:**
    1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (choose Windows build).
    2. Extract and add the `bin` folder to your system `PATH` environment variable.
    3. Test in terminal: `ffmpeg -version`

- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```

#### **Tesseract OCR** (for image recognition)

- **Windows:**
    1. Download the installer
       from [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) (see Releases).
    2. Install and add the install directory to your system `PATH`.
    3. Test in terminal: `tesseract --version`

- **Linux (Debian/Ubuntu):**

#### Protobuf
Compiling ```.proto``` files is MANDATORY to run the project
1. Install protoc 3.20.3:
    - Download from https://github.com/protocolbuffers/protobuf/releases/download/v3.20.3/protoc-3.20.3-win64.zip
    - Extract to a directory
    - Add the ```bin``` directory to ```PATH``` environment variable
    - Restart to make the change take effect
2. Navigate to Settings > Tools > External Tools
3. Add an external tool (+)
4. Fill in the following:
    - Program: ```protoc```
    - Arguments:
   ```bash 
   --python_out=$FileDir$ --pyi_out=$FileDir$ --proto_path=$FileDir$ $FilePath$
   ```
    - Working directory:
   ```bash
   $ProjectFileDir$
   ```
5. On a ```.proto``` file, right click, choose ```External Tools```. There will be a name corresponding to the created tool
6. There will be 2 files:
    - ```xxx_pb2.py```: descriptor of the class that will be implemented at runtime
    - ```xxx_pb2.pyi```: descriptor that supports Intellisense. DO NOT USE THIS FILE

Note:
1. ```.py``` generated  will have "errors", and you also don't see imports from this file. This is normal
2. ```protoc``` and ```protobuf``` must have the same version (3.20.3). Run these commands to check the version of ```protoc``` and ```protobuf``` respectively:
   ```bash
   protoc --version
   ```
   ```bash
   pip show protobuf
   ```

#### Running the project:

```bash
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ws websockets
```

Or

```bash
  uvicorn main:app --port 8000 --reload --ws websockets
```

## Usage

- Access the API docs at: http://localhost:8000/docs
- Example endpoints:
    - `GET /` - Health check
    - `GET /hello/{name}` - Greet by name

## Customization

- Add new endpoints in `routers/` and register them in `main.py`.
- Implement business logic in `services/`.
- Define data models in `models/`.
- Place helper functions in `utils/`.

---

For more details, see the code comments and FastAPI documentation.
fastapi
uvicorn
pydantic


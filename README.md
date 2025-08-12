# Alpha Mini Robot API

This project is a FastAPI backend for controlling and interacting with the Alpha Mini robot, including features for Osmo coding card recognition and audio conversion.

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
  1. Download the installer from [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) (see Releases).
  2. Install and add the install directory to your system `PATH`.
  3. Test in terminal: `tesseract --version`

- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt update && sudo apt install tesseract-ocr
  ```

### 3. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ws websockets
```

## Usage

- Access the API docs at: http://localhost:8000/docs
- Example endpoints:
  - `GET /` - Health check
  - `POST /osmo/parse_and_export` - Parse Osmo cards from JSON
  - `POST /osmo/recognize_from_image` - Parse Osmo cards from image
  - `POST /audio/convert` - Convert audio file to .wav

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

# Alpha Mini Robot API

This project is a FastAPI backend for controlling and interacting with the Alpha Mini robot.

## Project Structure

- `main.py`: Entry point, includes FastAPI app and router registration.
- `routers/`: Contains API route definitions.
- `models/`: Pydantic models for request/response schemas.
- `services/`: Business logic and robot control functions.
- `utils/`: Utility/helper functions.

## Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Run the server**

```bash
uvicorn main:app --reload
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


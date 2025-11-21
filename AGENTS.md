# Project Intercept

This project consists of two parts:
1. **Client (`intercept/client`)**: A Python application intended to run on Windows. It captures screenshots, sends them to the server, and executes received OS actions (mouse/keyboard).
2. **Server (`intercept/server`)**: A Python application (FastAPI) intended to run on Google Cloud Run. It receives screenshots, interacts with the Gemini model, and determines the next action.

## Architecture
- **Communication**: HTTP POST `json` containing the prompt and base64 encoded image (or multipart/form-data).
- **Action Protocol**: JSON response from server containing:
  - `action_type`: "click", "type", "press", "done", "fail"
  - `coordinates`: [x, y] (for clicks)
  - `text`: string (for typing)
  - `key`: string (for key presses)
  - `reasoning`: string (explanation of the step)

## Development
- The client uses `pyautogui` and `mss`.
- The server uses `fastapi` and `google-generativeai`.

import time
import json
import requests
import pyautogui
import mss
import mss.tools
import os
import sys
import uuid
import base64
from io import BytesIO
from PIL import Image

# Configuration
SERVER_URL = os.environ.get("INTERCEPT_SERVER_URL", "https://production-adk-agent-zb4zadb5da-ew.a.run.app")
MAX_STEPS = 20

def capture_screen():
    """Captures the full screen and returns it as bytes."""
    with mss.mss() as sct:
        # Capture the first monitor
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        # Convert to PNG bytes
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return buffered.getvalue()

def execute_action(action_data):
    """Executes the action received from the server."""
    action = action_data.get("action")
    thought = action_data.get("thought")
    print(f"\nThought: {thought}")
    print(f"Action: {action}")

    try:
        if action == "click":
            x = action_data.get("x")
            y = action_data.get("y")
            if x is not None and y is not None:
                pyautogui.click(x, y)

        elif action == "double_click":
            x = action_data.get("x")
            y = action_data.get("y")
            if x is not None and y is not None:
                pyautogui.doubleClick(x, y)

        elif action == "type":
            text = action_data.get("text")
            if text:
                pyautogui.write(text, interval=0.05)

        elif action == "press":
            key = action_data.get("key")
            if key:
                pyautogui.press(key)

        elif action == "wait":
            time.sleep(2)

        elif action == "done":
            print("Goal achieved!")
            return True

        elif action == "fail":
            print("Failed to achieve goal.")
            return True

    except Exception as e:
        print(f"Error executing action: {e}")

    return False

def main():
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        user_prompt = input("Enter your prompt (e.g., 'open chrome and search for shoes'): ")

    print(f"Starting task: {user_prompt}")

    # Generate a session ID for this task
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")

    # We still keep a local history just in case, but we rely on the server/db primarily
    previous_actions = []

    for step in range(MAX_STEPS):
        print(f"\n--- Step {step + 1} ---")

        # 1. Capture Screen
        print("Capturing screen...")
        image_bytes = capture_screen()

        # 2. Send to Server
        print("Sending to AI...")
        try:
            files = {'file': ('screenshot.png', image_bytes, 'image/png')}
            data = {
                'prompt': user_prompt,
                'session_id': session_id,
                'previous_actions': json.dumps(previous_actions)
            }

            response = requests.post(f"{SERVER_URL}/process", files=files, data=data)
            response.raise_for_status()
            action_data = response.json()

        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            break
        except json.JSONDecodeError:
            print("Invalid JSON response from server.")
            print(response.text)
            break

        # 3. Execute Action
        done = execute_action(action_data)

        # Update session ID if server returned a new one (should be same)
        if action_data.get("session_id"):
            session_id = action_data.get("session_id")

        # Record action for history
        previous_actions.append(action_data)

        if done:
            break

        time.sleep(1) # Brief pause between steps

if __name__ == "__main__":
    # PyAutoGUI fail-safe
    pyautogui.FAILSAFE = True
    main()

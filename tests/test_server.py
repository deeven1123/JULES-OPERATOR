import sys
from unittest.mock import MagicMock

# Mock google.cloud.firestore before importing the app
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.firestore"] = MagicMock()

from fastapi.testclient import TestClient
from intercept.server.main import app
import io

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    # The status might include firestore_enabled, check subset
    assert response.json().get("status") == "Server is running"

def test_process_step_mock():
    # Create a dummy image
    file_content = b"fake_image_data"

    # Mock data
    data = {
        "prompt": "test prompt",
        "previous_actions": "[]"
    }

    files = {
        "file": ("test.png", file_content, "image/png")
    }

    response = client.post("/process", data=data, files=files)
    assert response.status_code == 200
    json_response = response.json()

    # Check structure
    assert "thought" in json_response
    assert "action" in json_response
    assert "session_id" in json_response

    # Since we don't have an API key in the env, it should return the mock response
    if json_response["thought"] == "No API Key provided. Mocking a click action.":
        assert json_response["action"] == "click"
        assert json_response["x"] == 500

import os
import base64
import json
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from google.cloud import firestore
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all origins for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Configure Firestore
# Note: In Cloud Run, this will automatically use the service account.
# Locally, you need GOOGLE_APPLICATION_CREDENTIALS set.
try:
    db = firestore.Client()
    firestore_available = True
except Exception as e:
    print(f"Firestore initialization failed: {e}")
    firestore_available = False

class ActionResponse(BaseModel):
    thought: str
    action: str  # "click", "double_click", "type", "press", "wait", "done", "fail"
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None
    session_id: Optional[str] = None

SYSTEM_PROMPT = """
You are an autonomous agent running on a Windows computer.
Your goal is to accomplish the user's request by controlling the mouse and keyboard.
You will receive a screenshot of the current screen and the user's high-level request.

Output a JSON object describing the NEXT single action to take.
The available actions are:
- "click": Click the left mouse button at coordinates (x, y).
- "double_click": Double click the left mouse button at coordinates (x, y).
- "type": Type the specified string in "text".
- "press": Press a specific key (e.g., "enter", "backspace", "win") specified in "key".
- "wait": Wait for a moment (e.g., if loading).
- "done": The task is complete.
- "fail": The task cannot be completed.

Input screen size will be provided if possible, otherwise assume 1920x1080 but be careful.
Coordinate system: Top-left is (0,0).

Example response:
{
  "thought": "I need to open Chrome. I see the icon in the taskbar at 200, 1050.",
  "action": "click",
  "x": 200,
  "y": 1050
}

Respond ONLY with the JSON.
"""

@app.post("/process", response_model=ActionResponse)
async def process_step(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    session_id: str = Form(default=None),
    previous_actions_json: str = Form(alias="previous_actions", default="[]")
):
    # Ensure we have a session ID
    if not session_id:
        session_id = str(uuid.uuid4())

    # Retrieve history from Firestore if available and no local history provided
    history_context = []
    if firestore_available and session_id:
        try:
            doc_ref = db.collection("sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                history_context = data.get("history", [])
        except Exception as e:
            print(f"Error reading from Firestore: {e}")

    # If client provided history (fallback), usage depends on design.
    # Let's append client history if Firestore was empty, or just use Firestore.
    # To keep it simple: We will trust the Firestore history if it exists,
    # otherwise we use the client provided list.
    if not history_context and previous_actions_json:
        try:
            history_context = json.loads(previous_actions_json)
        except:
            pass

    if not GOOGLE_API_KEY:
        # Mock response for testing without API key
        return ActionResponse(
            thought="No API Key provided. Mocking a click action.",
            action="click",
            x=500,
            y=500,
            session_id=session_id
        )

    try:
        # Read the image file
        contents = await file.read()

        # Create the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prepare the input for Gemini
        full_prompt = [
            SYSTEM_PROMPT,
            f"User Goal: {prompt}",
            f"Previous Actions History: {json.dumps(history_context)}",
            "Current Screen State:",
            {"mime_type": file.content_type or "image/png", "data": contents}
        ]

        response = model.generate_content(full_prompt)

        # Extract JSON from response
        text_response = response.text.strip()

        # Simple cleanup
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]

        response_data = json.loads(text_response.strip())

        # Update Firestore with the new action
        if firestore_available:
            try:
                new_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_prompt": prompt,
                    "ai_response": response_data
                }
                # Update the document (create if not exists)
                doc_ref = db.collection("sessions").document(session_id)
                # Append to history array
                # In a real app, we might use arrayUnion, but we want to keep order and structure simple
                # Fetch, append, set is safer for simple structured data if low contention
                current_data = doc_ref.get().to_dict() or {"history": [], "created_at": datetime.utcnow().isoformat()}
                current_history = current_data.get("history", [])
                current_history.append(new_entry)

                doc_ref.set({
                    "history": current_history,
                    "last_updated": datetime.utcnow().isoformat()
                }, merge=True)

            except Exception as e:
                print(f"Error writing to Firestore: {e}")

        # Return the response with session_id so client can persist it
        return ActionResponse(**response_data, session_id=session_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Server is running", "firestore_enabled": firestore_available}

import os
import base64
import json
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
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

class ActionResponse(BaseModel):
    thought: str
    action: str  # "click", "double_click", "type", "press", "wait", "done", "fail"
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None

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
    previous_actions: str = Form(default="[]") # List of past actions for context
):
    if not GOOGLE_API_KEY:
        # Mock response for testing without API key
        return ActionResponse(
            thought="No API Key provided. Mocking a click action.",
            action="click",
            x=500,
            y=500
        )

    try:
        # Read the image file
        contents = await file.read()

        # Create the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prepare the input for Gemini
        # We pass the system prompt, the user prompt, previous context, and the image.

        full_prompt = [
            SYSTEM_PROMPT,
            f"User Goal: {prompt}",
            f"Previous Actions: {previous_actions}",
            "Current Screen State:",
            {"mime_type": file.content_type or "image/png", "data": contents}
        ]

        response = model.generate_content(full_prompt)

        # Extract JSON from response
        text_response = response.text.strip()

        # Simple cleanup if markdown code blocks are used
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]

        response_data = json.loads(text_response.strip())

        return ActionResponse(**response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Server is running"}

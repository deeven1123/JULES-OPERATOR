# Intercept: Autonomous Windows Agent

This application allows you to control your Windows computer using natural language prompts backed by Google Gemini.

## Prerequisites

1. **Python 3.10+** installed on your Windows machine.
2. **Google Cloud API Key** for Gemini.
3. **Google Cloud Project** with Firestore enabled (for session logging).

## Installation

1. Clone this repository or copy the files to your Windows machine.
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Application

You need two terminal windows.

### 1. Start the Server (Local)

The server handles the AI processing. While designed for Cloud Run, you can run it locally for testing.

```powershell
# Set your Google API Key
$env:GOOGLE_API_KEY = "your_api_key_here"

# Start the server
uvicorn intercept.server.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Run the Client (Agent)

The client captures your screen and executes actions.

```powershell
# The agent defaults to the Cloud Run production URL:
# https://production-adk-agent-zb4zadb5da-ew.a.run.app
# You can override it if testing locally:
# $env:INTERCEPT_SERVER_URL = "http://localhost:8000"

# Run the agent
python -m intercept.client.agent "open chrome and search for shoes on amazon"
```

## Cloud Deployment

To update the server code on Cloud Run (e.g., if you are the maintainer):

1. Use the provided `Dockerfile` (create one if missing based on previous instructions, or see below).
2. Deploy the `intercept/server` folder to the Cloud Run service `production-adk-agent`.

   ```dockerfile
   FROM python:3.9
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY intercept /app/intercept
   CMD ["uvicorn", "intercept.server.main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

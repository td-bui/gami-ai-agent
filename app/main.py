from fastapi import FastAPI, Body, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import base64
import os
from typing import Optional # Import Optional

from app.orchestrator import route_to_agent_stream
from app.agents.feedback import code_feedback
from app.agents.gamified_tuner import GamifiedTunerAgent

# --- App and CORS setup (Keep your hardcoded origins) ---
app = FastAPI()
ALLOW_ORIGINS = [
    "https://gami-ai.vercel.app",
    "https://gami-ai-be-production.up.railway.app",
    "http://localhost:3000"
]
print(f"CORS: Using hardcoded origins: {ALLOW_ORIGINS}", flush=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- JWT setup ---
JWT_SECRET_RAW = os.getenv("JWT_SECRET", "token_secret")
JWT_SECRET = base64.b64decode(JWT_SECRET_RAW)
JWT_ALGORITHM = "HS512"

# --- IMPORTANT CHANGE: Configure HTTPBearer to not auto-error ---
# This allows OPTIONS requests without an Authorization header to pass through.
security = HTTPBearer(auto_error=False)

# --- A single, robust JWT verification dependency ---
async def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # If no credentials are provided (e.g., for an OPTIONS request),
    # or if the scheme is not Bearer, raise an unauthorized error.
    if credentials is None or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        print("JWT decode error:", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token",
        )

# --- Apply the dependency to your protected endpoints ---

@app.post("/api/ai/orchestrate")
async def orchestrate_endpoint(
    user_input: str = Body(..., alias="userInput"),
    extra: dict = Body(default={}),
    user: dict = Depends(verify_jwt) # Use the new dependency
):
    return StreamingResponse(route_to_agent_stream(user_input, extra), media_type="text/plain")


@app.post("/api/ai/feedback")
async def feedback_endpoint(
    problem_title: str = Body(...),
    problem_description: str = Body(...),
    user_code: str = Body(...),
    running_result: str = Body(default=""),
    user: dict = Depends(verify_jwt) # Use the new dependency
):
    feedback = ""
    async for token in code_feedback(
        problem_title=problem_title,
        problem_description=problem_description,
        user_code=user_code,
        running_result=running_result,
    ):
        feedback += token
    return JSONResponse({"feedback": feedback})


# --- Your unprotected tuner endpoint remains the same ---
tuner_agent = GamifiedTunerAgent()
@app.post("/api/ai/tuner-step")
async def tuner_step(
    logs: dict = Body(...),
    user_action_metrics: dict = Body(...)
):
    action, updated_logs = tuner_agent.step(logs, user_action_metrics)
    return {"action": action, "logs": updated_logs}
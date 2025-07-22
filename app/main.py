from fastapi import FastAPI, Body, Depends, HTTPException, status, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import base64
import os
from app.orchestrator import route_to_agent_stream
from app.agents.feedback import code_feedback  # <-- Import feedback agent
from app.agents.gamified_tuner import GamifiedTunerAgent

# --- CORS setup ---
app = FastAPI()
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
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
security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
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

@app.post("/api/ai/orchestrate")
async def orchestrate_endpoint(
    user_input: str = Body(..., alias="userInput"),
    extra: dict = Body(default={}),
    user=Depends(verify_jwt)  # <-- JWT protection
):
    # route_to_agent_stream should return an async generator
    return StreamingResponse(route_to_agent_stream(user_input, extra), media_type="text/plain")

@app.post("/api/ai/feedback")
async def feedback_endpoint(
    problem_title: str = Body(...),
    problem_description: str = Body(...),
    user_code: str = Body(...),
    running_result: str = Body(default=""),
    user=Depends(verify_jwt)
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

# --- Router for Gamified Tuner Agent ---
# router = APIRouter()
tuner_agent = GamifiedTunerAgent()

@app.post("/api/ai/tuner-step")
async def tuner_step(
    logs: dict = Body(...),
    user_action_metrics: dict = Body(...)
):
    """
    Step the GamifiedTunerAgent with the current logs and user action metrics.
    Returns the chosen action and updated logs.
    """
    action, updated_logs = tuner_agent.step(logs, user_action_metrics)
    return {"action": action, "logs": updated_logs}
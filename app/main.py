from fastapi import FastAPI, Body, Depends, HTTPException, status, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import base64
import os
from app.orchestrator import route_to_agent_stream
from app.agents.feedback import code_feedback
from app.agents.gamified_tuner import GamifiedTunerAgent

# --- App and CORS setup ---
app = FastAPI()

# CHANGE THIS LINE to split by a comma ","
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")

print(f"CORS: Allowed Origins have been set to: {ALLOW_ORIGINS}", flush=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- JWT setup (no changes needed here) ---
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

# --- Create a new router for PROTECTED endpoints ---
# The JWT dependency is applied to the router, not each endpoint
protected_router = APIRouter(dependencies=[Depends(verify_jwt)])


@protected_router.post("/api/ai/orchestrate")
async def orchestrate_endpoint(
    user_input: str = Body(..., alias="userInput"),
    extra: dict = Body(default={})
    # No user=Depends() here anymore, it's on the router
):
    return StreamingResponse(route_to_agent_stream(user_input, extra), media_type="text/plain")


@protected_router.post("/api/ai/feedback")
async def feedback_endpoint(
    problem_title: str = Body(...),
    problem_description: str = Body(...),
    user_code: str = Body(...),
    running_result: str = Body(default="")
    # No user=Depends() here anymore, it's on the router
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


# --- Unprotected endpoints (like your tuner) stay on the main app ---
tuner_agent = GamifiedTunerAgent()
@app.post("/api/ai/tuner-step")
async def tuner_step(
    logs: dict = Body(...),
    user_action_metrics: dict = Body(...)
):
    action, updated_logs = tuner_agent.step(logs, user_action_metrics)
    return {"action": action, "logs": updated_logs}


# --- Include the protected router in the main app ---
app.include_router(protected_router)
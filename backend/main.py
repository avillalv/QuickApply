import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from routers import profile, jobs, applications, settings
from routers.automation import router as automation_router
from services.applicator import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="QuickApply API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(settings.router)
app.include_router(automation_router)

resumes_dir = os.path.join(os.path.dirname(__file__), "..", "resumes")
os.makedirs(resumes_dir, exist_ok=True)
app.mount("/resumes", StaticFiles(directory=resumes_dir), name="resumes")


@app.get("/")
async def root():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    db_status = "connected"
    try:
        from database import get_supabase
        sb = get_supabase()
        sb.table("settings").select("key").limit(1).execute()
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "healthy", "database": db_status}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session: str = Query(default="global"),
):
    """
    Session-aware WebSocket endpoint.

    Frontend connects with: ws://localhost:8000/ws?session=<session_id>
    First message can also include {type:"join", session_id:"..."} for
    post-connect session attachment.

    All messages from the frontend are routed to the matching AutomationSession
    so the background task can consume them.
    """
    await ws_manager.connect(websocket, session)
    try:
        while True:
            data = await websocket.receive_json()
            # Support post-connect session join
            if data.get("type") == "join":
                new_session = data.get("session_id", session)
                await ws_manager.disconnect(websocket, session)
                session = new_session
                await ws_manager.connect(websocket, session)
                await websocket.send_json({"type": "joined", "session_id": session})
            else:
                await ws_manager.route_message(data, session)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, session)
    except Exception:
        await ws_manager.disconnect(websocket, session)

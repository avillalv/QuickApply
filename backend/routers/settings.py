import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter

from database import get_supabase
from models import SettingItem

_PROFILES_DIR = Path(os.path.expanduser("~/.quickapply/profiles"))

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings():
    sb = get_supabase()
    result = sb.table("settings").select("*").execute()
    return {row["key"]: row["value"] for row in (result.data or [])}


@router.put("")
async def update_settings(items: List[SettingItem]):
    sb = get_supabase()
    for item in items:
        sb.table("settings").upsert({"key": item.key, "value": item.value}).execute()
    return {"status": "ok", "updated": len(items)}


@router.get("/{key}")
async def get_setting(key: str):
    sb = get_supabase()
    result = sb.table("settings").select("value").eq("key", key).execute()
    if not result.data:
        return {"key": key, "value": None}
    return {"key": key, "value": result.data[0]["value"]}


@router.post("/test-connections")
async def test_connections():
    results = {}

    # Test Supabase
    try:
        sb = get_supabase()
        sb.table("settings").select("key").limit(1).execute()
        results["supabase"] = {"status": "ok", "message": "Connected successfully"}
    except Exception as exc:
        results["supabase"] = {"status": "error", "message": str(exc)}

    # Test Anthropic
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            results["anthropic"] = {"status": "error", "message": "ANTHROPIC_API_KEY not set"}
        else:
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            results["anthropic"] = {"status": "ok", "message": "Connected successfully"}
    except Exception as exc:
        results["anthropic"] = {"status": "error", "message": str(exc)}

    return results


@router.post("/clear-browser-session")
async def clear_browser_session(channel: str = "chromium"):
    name = channel.strip() or "chromium"
    profile_dir = _PROFILES_DIR / name
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    return {"status": "cleared", "channel": name}

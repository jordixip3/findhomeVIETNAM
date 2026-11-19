import os, sys, asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.models.database import init_db
from app.routers import api

init_db()

app = FastAPI(title="FindHome Vietnam — Nền Tảng Nhà Ở Chia Sẻ & Co-Living Tại Việt Nam", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def log_middleware(request, call_next):
    resp = await call_next(request)
    path = request.url.path
    if not any(path.endswith(e) for e in [".css", ".js", ".jpg", ".png"]) and not "/static" in path:
        try:
            from app.services.geoip_service import extract_client_ip, resolve_geoip, detect_device_type
            from app.models.database import record_access_log
            h = dict(request.headers)
            ip = extract_client_ip(h)
            record_access_log(ip, "Global", "AS", "", "Metro", 0.0, 0.0, path, request.method, resp.status_code, h.get("user-agent", ""), detect_device_type(h.get("user-agent", "")))
        except Exception: pass
    return resp

app.include_router(api.router)

sdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(sdir):
    app.mount("/static", StaticFiles(directory=sdir), name="static")
    app.mount("/VIETNAM/static", StaticFiles(directory=sdir), name="static_r")
    app.mount("/vietnam/static", StaticFiles(directory=sdir), name="static_rl")

@app.get("/", include_in_schema=False)
@app.get("/VIETNAM", include_in_schema=False)
@app.get("/VIETNAM/", include_in_schema=False)
@app.get("/vietnam", include_in_schema=False)
@app.get("/vietnam/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(sdir, "index.html"), headers={"Cache-Control": "no-cache"})

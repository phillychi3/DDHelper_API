import logging
from enum import Enum
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database_schema import VtuberDatabase

logger = logging.getLogger("vtuber_api")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("vtuber_api.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("[VtuberAPI] %(asctime)s %(levelname)s: %(message)s"))
logger.addHandler(handler)

app = FastAPI(
    title="VTuber Tracker API",
    description="API for tracking VTubers, their channels, videos, and live streams",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db = None
collector = None


class LiveStatus(str, Enum):
    LIVE = "LIVE"
    READY_TO_LIVE = "READY_TO_LIVE"


class Platform(str, Enum):
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    ALL = "all"


# Define response models
class VTuber(BaseModel):
    name: str
    company: str = ""
    country: str = ""
    channel_url: str
    platform: str
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0
    activity_status: str = ""
    debut_date: str = ""
    thumbnail: str = ""
    channel_id: str


class VideoInfo(BaseModel):
    video_id: str
    title: str
    description: str = ""
    published_at: str = ""
    channel_id: str = ""
    channel_title: str = ""
    thumbnail: str = ""
    view_count: int = 0
    like_count: int = 0
    collaborators: list[dict[str, str]] = []


class LiveInfo(BaseModel):
    status: str | None = None
    channel: str
    video_id: str | None = None
    title: str | None = None
    thumbnail: str | None = None
    platform: str
    timestamp: float | None = None


class ControllerStatus(BaseModel):
    current_task: str
    current_channel: str | None = None
    total_channels: int
    checked_channels: int
    last_check_start: float | None = None
    last_check_end: float | None = None
    next_check_time: float | None = None
    api_quota_used: int
    api_quota_limit: int
    api_quota_exceeded: bool
    api_quota_reset_time: float
    ready_live_count: int
    is_running: bool
    errors: list[dict] = []


controller = None


def init_api(database, tracker_controller=None):
    """Initialize the API with database and controller instances."""
    global db, controller
    db = database
    controller = tracker_controller


def get_controller():
    """Dependency for controller access."""
    if controller is None:
        raise HTTPException(status_code=500, detail="Controller not available")
    return controller


def get_db():
    """Dependency for database access."""
    if db is None:
        raise HTTPException(status_code=500, detail="API not fully initialized - database missing")
    return db


@app.get("/status", response_model=ControllerStatus, tags=["System"])
async def get_controller_status(controller=Depends(get_controller)):
    """Get current controller status and progress."""
    try:
        status = controller.get_status()
        return status
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get controller status")


@app.get("/live", response_model=list[LiveInfo], tags=["Live Streams"])
async def get_live(
    status: LiveStatus = Query(LiveStatus.LIVE, description="Filter by live status"),
    platform: Platform = Query(Platform.ALL, description="Filter by platform"),
    db: VtuberDatabase = Depends(get_db),
):
    """Get live or scheduled streams."""
    livedata = list(db.getlivefromstatus(status))

    # Filter by platform if needed
    if platform != Platform.ALL:
        livedata = [stream for stream in livedata if stream.get("platform") == platform]

    # Remove MongoDB IDs
    for page in range(len(livedata)):
        if "_id" in livedata[page]:
            del livedata[page]["_id"]

    return livedata


@app.get("/allvtuber", response_model=list[VTuber], tags=["VTubers"])
async def get_all_vtuber(db: VtuberDatabase = Depends(get_db)):
    """Get all VTuber information."""
    return db.get_channels()


@app.get("/vtuber/{channel_id}", response_model=dict[str, Any], tags=["VTubers"])
async def get_vtuber(channel_id: str, db: VtuberDatabase = Depends(get_db)):
    """Get detailed information for a specific VTuber."""
    vtuber = db.get_channel(channel_id)
    if not vtuber:
        raise HTTPException(status_code=404, detail="VTuber not found")

    # Remove MongoDB ID
    if "_id" in vtuber:
        del vtuber["_id"]

    return vtuber


@app.get("/videos/{channel_id}", response_model=list[VideoInfo], tags=["Videos"])
async def get_channel_videos(
    channel_id: str,
    limit: int = Query(50, description="Results limit"),
    skip: int = Query(0, description="Results offset"),
    db: VtuberDatabase = Depends(get_db),
):
    """Get videos for a specific channel."""
    videos = db.get_channel_videos(channel_id, limit, skip)

    # Remove MongoDB IDs
    for video in videos:
        if "_id" in video:
            del video["_id"]

    return videos


@app.get("/video/{video_id}", response_model=VideoInfo, tags=["Videos"])
async def get_video(video_id: str, db: VtuberDatabase = Depends(get_db)):
    """Get details for a specific video."""
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Remove MongoDB ID
    if "_id" in video:
        del video["_id"]

    return video


@app.get("/search/vtubers", response_model=list[VTuber], tags=["Search"])
async def search_vtubers(
    q: str = Query("", description="Search query"),
    limit: int = Query(50, description="Results limit"),
    skip: int = Query(0, description="Results offset"),
    db: VtuberDatabase = Depends(get_db),
):
    """Search for VTubers by query."""
    if not q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    results = db.search_channels(q, limit, skip)

    # Remove MongoDB IDs
    for result in results:
        if "_id" in result:
            del result["_id"]

    return results


@app.get("/search/videos", response_model=list[VideoInfo], tags=["Search"])
async def search_videos(
    q: str = Query("", description="Search query"),
    limit: int = Query(50, description="Results limit"),
    skip: int = Query(0, description="Results offset"),
    db: VtuberDatabase = Depends(get_db),
):
    """Search for videos by query."""
    if not q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    results = db.search_videos(q, limit, skip)

    # Remove MongoDB IDs
    for result in results:
        if "_id" in result:
            del result["_id"]

    return results


@app.get("/collabs/{channel_id}", response_model=list[VideoInfo], tags=["Collaborations"])
async def get_collabs(
    channel_id: str,
    limit: int = Query(50, description="Results limit"),
    skip: int = Query(0, description="Results offset"),
    db: VtuberDatabase = Depends(get_db),
):
    """Get collaborations for a specific channel."""
    videos = db.get_collaborations(channel_id, limit, skip)

    # Remove MongoDB IDs
    for video in videos:
        if "_id" in video:
            del video["_id"]

    return videos


@app.get("/filter/vtubers", response_model=list[VTuber], tags=["VTubers"])
async def filter_vtubers(
    company: str | None = Query(None, description="Filter by company"),
    country: str | None = Query(None, description="Filter by country"),
    platform: Platform = Query(Platform.YOUTUBE, description="Filter by platform"),
    limit: int = Query(50, description="Results limit"),
    skip: int = Query(0, description="Results offset"),
    db: VtuberDatabase = Depends(get_db),
):
    """Filter VTubers by company, country, etc."""
    # Build filter
    filter_dict = {}
    if company:
        filter_dict["company"] = company
    if country:
        filter_dict["country"] = country
    if platform != Platform.ALL:
        filter_dict["platform"] = platform.value

    results = db.get_channels_by_filter(filter_dict)

    # Apply pagination and remove MongoDB IDs
    results = results[skip : skip + limit]
    for result in results:
        if "_id" in result:
            del result["_id"]

    return results


@app.get("/ping", tags=["System"])
async def ping():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "pong"}


def start(host: str = "0.0.0.0", port: int = 7600, debug: bool = False):
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info", reload=debug)

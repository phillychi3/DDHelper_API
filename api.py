import logging
from enum import Enum
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database_schema import VtuberDatabase, extract_channel_id_from_url
from vtuber import extract_channel_id

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


class VTuberCreate(BaseModel):
    name: str
    channel_id: str
    channel_url: str
    platform: str = "youtube"
    company: str = ""
    country: str = ""
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0
    activity_status: str = "active"
    debut_date: str = ""
    thumbnail: str = ""


class VTuberUpdate(BaseModel):
    name: str | None = None
    channel_url: str | None = None
    platform: str | None = None
    company: str | None = None
    country: str | None = None
    subscriber_count: int | None = None
    view_count: int | None = None
    video_count: int | None = None
    activity_status: str | None = None
    debut_date: str | None = None
    thumbnail: str | None = None


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
    vtuber: VTuber | None = None


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
    """Get live or scheduled streams with vtuber data."""
    livedata = list(db.getlivefromstatus(status))

    # Filter by platform if needed
    if platform != Platform.ALL:
        livedata = [stream for stream in livedata if stream.get("platform") == platform]

    # Remove MongoDB IDs and attach vtuber data
    for stream in livedata:
        if "_id" in stream:
            del stream["_id"]

        # Look up vtuber data by channel_url
        channel_url = stream.get("channel", "")
        vtuber_data = db.get_channel_by_url(channel_url)
        if vtuber_data:
            vtuber_data.pop("_id", None)
            raw_channel_id = vtuber_data.get("channel_id", "")
            clean_id = extract_channel_id_from_url(raw_channel_id)
            if not clean_id:
                clean_id = extract_channel_id_from_url(vtuber_data.get("channel_url", ""))
            vtuber_data["channel_id"] = clean_id
            stream["vtuber"] = vtuber_data

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


@app.post("/vtuber", response_model=dict[str, str], tags=["VTubers Management"])
async def create_vtuber(vtuber: VTuberCreate, db: VtuberDatabase = Depends(get_db)):
    """Create a new VTuber entry."""
    # Resolve the real UC channel ID (handles @handle -> UCxxxx conversion)
    real_channel_id = extract_channel_id(vtuber.channel_id)

    # Multi-method duplicate check
    existing = db.get_channel(real_channel_id)

    if not existing:
        existing = db.get_channel_by_url(vtuber.channel_url)

    if not existing and "@" in vtuber.channel_id:
        handle = vtuber.channel_id.lstrip("@")
        existing = db.find_channel_by_handle(handle)

    if existing:
        existing_name = existing.get("name", "Unknown")
        raise HTTPException(
            status_code=400,
            detail=f"VTuber already exists: {existing_name} (matched by channel_id or handle)",
        )

    # Insert channel with resolved channel_id
    channel_data = vtuber.model_dump()
    channel_data["channel_id"] = real_channel_id
    success = db.insert_channel(channel_data)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create VTuber")

    logger.info(f"Created VTuber: {vtuber.name} ({real_channel_id})")
    return {"message": "VTuber created successfully", "channel_id": real_channel_id}


@app.put("/vtuber/{channel_id}", response_model=dict[str, str], tags=["VTubers Management"])
async def update_vtuber(
    channel_id: str, vtuber_update: VTuberUpdate, db: VtuberDatabase = Depends(get_db)
):
    """Update an existing VTuber entry."""
    # Check if channel exists
    existing = db.get_channel(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="VTuber not found")

    # Filter out None values
    update_data = {k: v for k, v in vtuber_update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Update channel
    success = db.update_channel_by_id(channel_id, update_data)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update VTuber")

    logger.info(f"Updated VTuber: {channel_id}")
    return {"message": "VTuber updated successfully", "channel_id": channel_id}


@app.delete("/vtuber/{channel_id}", response_model=dict[str, str], tags=["VTubers Management"])
async def delete_vtuber(channel_id: str, db: VtuberDatabase = Depends(get_db)):
    """Delete a VTuber entry."""
    # Check if channel exists
    existing = db.get_channel(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="VTuber not found")

    # Delete channel
    success = db.delete_channel_by_id(channel_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete VTuber")

    logger.info(f"Deleted VTuber: {channel_id}")
    return {"message": "VTuber deleted successfully", "channel_id": channel_id}


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


@app.get("/debug/channel/{channel_id}", tags=["Debug"])
async def debug_channel(channel_id: str, db: VtuberDatabase = Depends(get_db)):
    """Debug endpoint to see raw channel data from database."""
    # Try to find by channel_id
    raw_data = db.db.channel.find_one({"channel_id": channel_id})

    if not raw_data:
        # Try to find by channel_url if channel_id lookup fails
        raw_data = db.db.channel.find_one({"channel_url": channel_id})

    if not raw_data:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Convert ObjectId to string for JSON serialization
    if "_id" in raw_data:
        raw_data["_id"] = str(raw_data["_id"])

    return {"raw_data": raw_data, "message": "This is the raw data from MongoDB"}


@app.get("/debug/find-by-url", tags=["Debug"])
async def debug_find_by_url(url: str, db: VtuberDatabase = Depends(get_db)):
    """Debug endpoint to find channel by exact channel_url match."""
    raw_data = db.db.channel.find_one({"channel_url": url})

    if not raw_data:
        raise HTTPException(status_code=404, detail=f"No channel found with channel_url: {url}")

    # Convert ObjectId to string for JSON serialization
    if "_id" in raw_data:
        raw_data["_id"] = str(raw_data["_id"])

    return {"raw_data": raw_data, "message": "Found by channel_url"}


def start(host: str = "0.0.0.0", port: int = 7600, debug: bool = False):
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info", reload=debug)

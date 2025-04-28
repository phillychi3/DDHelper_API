from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from database_schema import VtuberDatabase
from vtuber_collector import VtuberCollector
import uvicorn
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger("vtuber_api")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("vtuber_api.log", encoding="utf-8")
handler.setFormatter(
    logging.Formatter("[VtuberAPI] %(asctime)s %(levelname)s: %(message)s")
)
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
    collaborators: List[Dict[str, str]] = []


class LiveInfo(BaseModel):
    status: Optional[str] = None
    channel: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    platform: str
    timestamp: Optional[float] = None


def init_api(database, vtuber_collector):
    """Initialize the API with database and collector instances."""
    global db, collector
    db = database
    collector = vtuber_collector


def get_db():
    """Dependency for database access."""
    if db is None:
        raise HTTPException(
            status_code=500, detail="API not fully initialized - database missing"
        )
    return db


def get_collector():
    """Dependency for collector access."""
    if collector is None:
        raise HTTPException(
            status_code=500, detail="API not fully initialized - collector missing"
        )
    return collector


@app.get("/live", response_model=List[LiveInfo], tags=["Live Streams"])
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


@app.get("/allvtuber", response_model=List[VTuber], tags=["VTubers"])
async def get_all_vtuber(db: VtuberDatabase = Depends(get_db)):
    """Get all VTuber information."""
    return db.get_channels()


@app.get("/vtuber/{channel_id}", response_model=Dict[str, Any], tags=["VTubers"])
async def get_vtuber(channel_id: str, db: VtuberDatabase = Depends(get_db)):
    """Get detailed information for a specific VTuber."""
    vtuber = db.get_channel(channel_id)
    if not vtuber:
        raise HTTPException(status_code=404, detail="VTuber not found")

    # Remove MongoDB ID
    if "_id" in vtuber:
        del vtuber["_id"]

    return vtuber


@app.get("/videos/{channel_id}", response_model=List[VideoInfo], tags=["Videos"])
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


@app.get("/search/vtubers", response_model=List[VTuber], tags=["Search"])
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


@app.get("/search/videos", response_model=List[VideoInfo], tags=["Search"])
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


@app.get(
    "/collabs/{channel_id}", response_model=List[VideoInfo], tags=["Collaborations"]
)
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


@app.get("/filter/vtubers", response_model=List[VTuber], tags=["VTubers"])
async def filter_vtubers(
    company: Optional[str] = Query(None, description="Filter by company"),
    country: Optional[str] = Query(None, description="Filter by country"),
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


@app.get("/check-live/{channel_url_or_id}", response_model=LiveInfo, tags=["Testing"])
async def check_live(
    channel_url_or_id: str,
    platform: Platform = Query(Platform.YOUTUBE, description="Platform to check"),
    collector: VtuberCollector = Depends(get_collector),
):
    """Manually check if a channel is live (for testing)."""
    try:
        if platform == Platform.YOUTUBE:
            result = collector.get_live_status(channel_url_or_id)
        elif platform == Platform.TWITCH:
            result = collector.get_twitch_status(channel_url_or_id)
        else:
            raise HTTPException(status_code=400, detail="Platform not supported")

        return result
    except Exception as e:
        logger.error(f"Error checking live status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/update-channel/{channel_url_or_id}",
    response_model=Dict[str, Any],
    tags=["Testing"],
)
async def update_channel(
    channel_url_or_id: str,
    platform: Platform = Query(Platform.YOUTUBE, description="Platform to update"),
    collector: VtuberCollector = Depends(get_collector),
    db: VtuberDatabase = Depends(get_db),
):
    """Manually update channel data (for testing)."""
    try:
        if platform == Platform.YOUTUBE:
            channel_data = collector.get_channel_info(channel_url_or_id)
        elif platform == Platform.TWITCH:
            channel_data = collector.get_channel_by_platform(
                "twitch", channel_url_or_id
            )
        else:
            raise HTTPException(status_code=400, detail="Platform not supported")

        db.insert_channel(channel_data)

        # Remove MongoDB ID
        if "_id" in channel_data:
            del channel_data["_id"]

        return channel_data
    except Exception as e:
        logger.error(f"Error updating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start(host="0.0.0.0", port=7600, debug=False):
    """Start the FastAPI server using uvicorn."""
    uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")


if __name__ == "__main__":
    start()

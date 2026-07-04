import logging
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
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
    ALL = "ALL"


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


class Company(BaseModel):
    name: str
    youtube: str = ""
    twitter: str = ""
    vtuber_count: int = 0


class CompanyCreate(BaseModel):
    name: str
    youtube: str = ""
    twitter: str = ""


class CompanyUpdate(BaseModel):
    name: str | None = None
    youtube: str | None = None
    twitter: str | None = None


class BatchAssignRequest(BaseModel):
    channel_ids: list[str]


class Country(BaseModel):
    name: str
    vtuber_count: int = 0


class CountryCreate(BaseModel):
    name: str


class CountryUpdate(BaseModel):
    name: str | None = None


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

management_router = APIRouter()
debug_router = APIRouter()


def init_api(database, tracker_controller=None, dev_mode=False):
    """Initialize the API with database and controller instances."""
    global db, controller
    db = database
    controller = tracker_controller
    if dev_mode:
        app.include_router(management_router)
        app.include_router(debug_router)
        logger.info("Dev mode: management and debug routes are enabled")


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
    status: LiveStatus = Query(LiveStatus.ALL, description="Filter by live status"),
    platform: Platform = Query(Platform.ALL, description="Filter by platform"),
    db: VtuberDatabase = Depends(get_db),
):
    """Get live or scheduled streams with vtuber data."""
    if status == LiveStatus.ALL:
        livedata = list(db.get_all_live())
    else:
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


@management_router.post("/vtuber", response_model=dict[str, str], tags=["VTubers Management"])
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


@management_router.put("/vtuber/{channel_id}", response_model=dict[str, str], tags=["VTubers Management"])
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


@management_router.delete("/vtuber/{channel_id}", response_model=dict[str, str], tags=["VTubers Management"])
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


@app.get("/companies", response_model=list[Company], tags=["Companies"])
async def get_companies(db: VtuberDatabase = Depends(get_db)):
    """Get all companies with vtuber counts."""
    return db.get_all_companies()


@management_router.post("/company", response_model=dict[str, str], tags=["Companies"])
async def create_company(company: CompanyCreate, db: VtuberDatabase = Depends(get_db)):
    """Create a new company."""
    existing = db.db.companies.find_one({"name": company.name})
    if existing:
        raise HTTPException(status_code=400, detail=f"Company '{company.name}' already exists")
    success = db.create_company(company.name, company.youtube, company.twitter)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create company")
    logger.info(f"Created company: {company.name}")
    return {"message": "Company created successfully", "name": company.name}


@management_router.put("/company/{company_name}", response_model=dict[str, str], tags=["Companies"])
async def update_company(
    company_name: str, company_update: CompanyUpdate, db: VtuberDatabase = Depends(get_db)
):
    """Update a company (rename and/or change description). Renaming also updates all vtubers."""
    existing = db.db.companies.find_one({"name": company_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    if company_update.name and company_update.name != company_name:
        conflict = db.db.companies.find_one({"name": company_update.name})
        if conflict:
            raise HTTPException(
                status_code=400, detail=f"Company '{company_update.name}' already exists"
            )
    success = db.update_company(company_name, company_update.name, company_update.youtube, company_update.twitter)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update company")
    final_name = company_update.name or company_name
    logger.info(f"Updated company: {company_name} -> {final_name}")
    return {"message": "Company updated successfully", "name": final_name}


@management_router.delete("/company/{company_name}", response_model=dict[str, str], tags=["Companies"])
async def delete_company(company_name: str, db: VtuberDatabase = Depends(get_db)):
    """Delete a company and clear its vtubers' company field."""
    existing = db.db.companies.find_one({"name": company_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    success = db.delete_company(company_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete company")
    logger.info(f"Deleted company: {company_name}")
    return {"message": "Company deleted successfully", "name": company_name}


@app.get("/company/{company_name}/vtubers", response_model=list[VTuber], tags=["Companies"])
async def get_company_vtubers(company_name: str, db: VtuberDatabase = Depends(get_db)):
    """Get all vtubers belonging to a company."""
    existing = db.db.companies.find_one({"name": company_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    return db.get_company_vtubers(company_name)


@management_router.put(
    "/company/{company_name}/vtubers/batch",
    response_model=dict[str, Any],
    tags=["Companies"],
)
async def batch_assign_company(
    company_name: str,
    body: BatchAssignRequest,
    db: VtuberDatabase = Depends(get_db),
):
    """Batch-set the exact vtuber members of a company. Vtubers not in the list are unassigned."""
    existing = db.db.companies.find_one({"name": company_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    result = db.batch_assign_company(company_name, body.channel_ids)
    logger.info(f"Batch assign company '{company_name}': {result}")
    return {"message": "Batch assignment complete", **result}


@app.get("/countries", response_model=list[Country], tags=["Countries"])
async def get_countries(db: VtuberDatabase = Depends(get_db)):
    """Get all countries with vtuber counts."""
    return db.get_all_countries()


@management_router.post("/country", response_model=dict[str, str], tags=["Countries"])
async def create_country(country: CountryCreate, db: VtuberDatabase = Depends(get_db)):
    """Create a new country."""
    existing = db.db.countries.find_one({"name": country.name})
    if existing:
        raise HTTPException(status_code=400, detail=f"Country '{country.name}' already exists")
    success = db.create_country(country.name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create country")
    logger.info(f"Created country: {country.name}")
    return {"message": "Country created successfully", "name": country.name}


@management_router.put("/country/{country_name}", response_model=dict[str, str], tags=["Countries"])
async def update_country(
    country_name: str, country_update: CountryUpdate, db: VtuberDatabase = Depends(get_db)
):
    """Update a country. Renaming also updates all vtubers."""
    existing = db.db.countries.find_one({"name": country_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Country not found")
    if country_update.name and country_update.name != country_name:
        conflict = db.db.countries.find_one({"name": country_update.name})
        if conflict:
            raise HTTPException(
                status_code=400, detail=f"Country '{country_update.name}' already exists"
            )
    success = db.update_country(country_name, country_update.name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update country")
    final_name = country_update.name or country_name
    logger.info(f"Updated country: {country_name} -> {final_name}")
    return {"message": "Country updated successfully", "name": final_name}


@management_router.delete("/country/{country_name}", response_model=dict[str, str], tags=["Countries"])
async def delete_country(country_name: str, db: VtuberDatabase = Depends(get_db)):
    """Delete a country and clear its vtubers' country field."""
    existing = db.db.countries.find_one({"name": country_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Country not found")
    success = db.delete_country(country_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete country")
    logger.info(f"Deleted country: {country_name}")
    return {"message": "Country deleted successfully", "name": country_name}


@app.get("/country/{country_name}/vtubers", response_model=list[VTuber], tags=["Countries"])
async def get_country_vtubers(country_name: str, db: VtuberDatabase = Depends(get_db)):
    """Get all vtubers belonging to a country."""
    existing = db.db.countries.find_one({"name": country_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Country not found")
    return db.get_country_vtubers(country_name)


@management_router.put(
    "/country/{country_name}/vtubers/batch",
    response_model=dict[str, Any],
    tags=["Countries"],
)
async def batch_assign_country(
    country_name: str,
    body: BatchAssignRequest,
    db: VtuberDatabase = Depends(get_db),
):
    """Batch-set the exact vtuber members of a country."""
    existing = db.db.countries.find_one({"name": country_name})
    if not existing:
        raise HTTPException(status_code=404, detail="Country not found")
    result = db.batch_assign_country(country_name, body.channel_ids)
    logger.info(f"Batch assign country '{country_name}': {result}")
    return {"message": "Batch assignment complete", **result}


@app.get("/ping", tags=["System"])
async def ping():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "pong"}


@debug_router.get("/debug/channel/{channel_id}", tags=["Debug"])
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


@debug_router.get("/debug/find-by-url", tags=["Debug"])
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

    uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")

# VTuber Tracker System

A comprehensive system for tracking VTubers across platforms, with focus on YouTube. This system monitors live streams, collects channel statistics, and analyzes video collaborations.

## Features

- **Live Stream Tracking**: Monitor which VTubers are live or have upcoming streams
- **Channel Statistics**: Collect and store subscriber counts, view counts, and other metrics
- **Collaboration Detection**: Identify when VTubers collaborate with each other
- **Hybrid Data Collection**: Use YouTube's official API when available, fall back to scraping when API limits are reached
- **REST API**: Access all data through a simple REST API

## System Components

1. **VTuber Collector**: Handles data collection from YouTube (API or scraping)
2. **Database Schema**: MongoDB structure for storing all VTuber information
3. **Control Logic**: Manages periodic checks for live streams, channel updates, and video analysis
4. **API Server**: FastAPI-based REST endpoints for accessing the collected data

## Requirements

- Python 3.10+
- MongoDB
- Google API key (for YouTube Data API v3)
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/vtuber-tracker.git
   cd vtuber-tracker
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Configure the system:

   - Copy `config.yaml.example` to `config.yaml`
   - Add your MongoDB connection string
   - Add your YouTube API key

4. Run the system:
   ```
   python main.py
   ```

## Configuration

Edit `config.yaml` to customize:

- Database connection
- YouTube API key
- API call limits
- API server settings
- Update intervals

## API Documentation

The system provides auto-generated API documentation using Swagger UI. Once the system is running, you can access:

- Swagger UI: `http://localhost:7600/docs`
- ReDoc: `http://localhost:7600/redoc`

### Main API Endpoints

| Endpoint                | Method | Description                               |
| ----------------------- | ------ | ----------------------------------------- |
| `/live`                 | GET    | Get currently live VTubers                |
| `/allvtuber`            | GET    | Get all tracked VTubers                   |
| `/vtuber/{channel_id}`  | GET    | Get details for a specific VTuber         |
| `/videos/{channel_id}`  | GET    | Get videos for a specific channel         |
| `/video/{video_id}`     | GET    | Get details for a specific video          |
| `/search/vtubers`       | GET    | Search for VTubers by query               |
| `/search/videos`        | GET    | Search for videos by query                |
| `/collabs/{channel_id}` | GET    | Get collaborations for a specific channel |
| `/filter/vtubers`       | GET    | Filter VTubers by company, country, etc.  |
| `/ping`                 | GET    | Health check endpoint                     |

## Adding New VTubers

To add a new VTuber to the system, use the `add_vtuber.py` script:

```
python scripts/add_vtuber.py --channel_id UCL_gCybOJRIgOXw6Qb4qJzQ
```

Or add directly to the MongoDB database with the following structure:

```json
{
  "channel_id": "UCL_gCybOJRIgOXw6Qb4qJzQ",
  "name": "Korone Ch. 戌神ころね",
  "company": "Hololive",
  "country": "Japan",
  "channel_url": "https://www.youtube.com/channel/UCL_gCybOJRIgOXw6Qb4qJzQ",
  "platform": "youtube"
}
```

## Monitoring Live Streams

The system automatically checks if VTubers are live or have upcoming streams, and exposes this information through the `/live` endpoint:

```
GET /live?status=LIVE         # Currently live VTubers
GET /live?status=READY_TO_LIVE # VTubers with upcoming streams
```

## Data Collection

The system uses a hybrid approach for data collection:

1. First tries to use the YouTube Data API v3
2. If API quota is exhausted, falls back to web scraping

This ensures maximum reliability while respecting API limits.

## Schema

### Channel Data

```
{
  "channel_id": "...",
  "name": "...",
  "description": "...",
  "custom_url": "...",
  "published_at": "...",
  "thumbnail": "...",
  "country": "...",
  "view_count": 123456,
  "subscriber_count": 123456,
  "video_count": 123,
  "company": "...",
  "activity_status": "active",
  "debut_date": "...",
  "platform": "youtube",
  "channel_url": "..."
}
```

### Video Data

```
{
  "video_id": "...",
  "title": "...",
  "description": "...",
  "published_at": "...",
  "channel_id": "...",
  "channel_title": "...",
  "tags": ["...", "..."],
  "category_id": "...",
  "thumbnail": "...",
  "duration": "...",
  "view_count": 123456,
  "like_count": 123456,
  "comment_count": 123456,
  "collaborators": [
    {
      "channel_id": "...",
      "platform": "youtube"
    },
    ...
  ]
}
```

### Live Stream Data

```
{
  "status": "LIVE",
  "channel": "https://www.youtube.com/channel/...",
  "video_id": "...",
  "title": "...",
  "thumbnail": "...",
  "platform": "youtube",
  "timestamp": 1234567890
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, date, timedelta
import pytz


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class BadDeed(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None  # For future multi-user support
    notes: Optional[str] = None    # Optional notes about the bad deed

class BadDeedResponse(BaseModel):
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    notes: Optional[str] = None

class BadDeedCreate(BaseModel):
    notes: Optional[str] = None

class StatsResponse(BaseModel):
    count: int
    date: str
    day_of_week: str


# Helper functions
def get_today_start_end():
    """Get start and end of today in UTC"""
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())
    return today_start, today_end


# API Routes
@api_router.get("/")
async def root():
    return {"message": "Bad Deeds Tracker API"}

@api_router.post("/bad-deed", response_model=BadDeedResponse)
async def record_bad_deed(input: BadDeedCreate):
    """Record a new bad deed"""
    try:
        bad_deed = BadDeed(**input.dict())
        await db.bad_deeds.insert_one(bad_deed.dict())
        return BadDeedResponse(**bad_deed.dict())
    except Exception as e:
        logging.error(f"Error recording bad deed: {e}")
        raise HTTPException(status_code=500, detail="Failed to record bad deed")

@api_router.get("/bad-deeds", response_model=List[BadDeedResponse])
async def get_bad_deeds(limit: int = 100):
    """Get all bad deeds (most recent first)"""
    try:
        bad_deeds = await db.bad_deeds.find().sort("timestamp", -1).limit(limit).to_list(limit)
        return [BadDeedResponse(**deed) for deed in bad_deeds]
    except Exception as e:
        logging.error(f"Error fetching bad deeds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bad deeds")

@api_router.get("/stats/today", response_model=StatsResponse)
async def get_today_stats():
    """Get today's bad deed count"""
    try:
        today_start, today_end = get_today_start_end()
        
        count = await db.bad_deeds.count_documents({
            "timestamp": {
                "$gte": today_start,
                "$lte": today_end
            }
        })
        
        today = datetime.utcnow().date()
        day_of_week = today.strftime("%A")
        
        return StatsResponse(
            count=count,
            date=today.isoformat(),
            day_of_week=day_of_week
        )
    except Exception as e:
        logging.error(f"Error getting today's stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get today's stats")

@api_router.get("/stats/recent")
async def get_recent_stats(days: int = 7):
    """Get stats for recent days"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Create aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": datetime.combine(start_date, datetime.min.time()),
                        "$lte": datetime.combine(end_date, datetime.max.time())
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$timestamp"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await db.bad_deeds.aggregate(pipeline).to_list(days)
        
        # Fill in missing days with 0 count
        stats = []
        current_date = start_date
        results_dict = {result["_id"]: result["count"] for result in results}
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            count = results_dict.get(date_str, 0)
            day_of_week = current_date.strftime("%A")
            
            stats.append({
                "date": date_str,
                "count": count,
                "day_of_week": day_of_week
            })
            current_date += timedelta(days=1)
        
        return {"stats": stats}
    except Exception as e:
        logging.error(f"Error getting recent stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent stats")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

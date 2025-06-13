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

@api_router.get("/stats/day-of-week")
async def get_day_of_week_analysis():
    """Get day-of-week pattern analysis"""
    try:
        # Get data for the last 8 weeks (56 days) for better pattern analysis
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=55)
        
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
                        "$dayOfWeek": "$timestamp"
                    },
                    "count": {"$sum": 1},
                    "dates": {
                        "$push": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$timestamp"
                            }
                        }
                    }
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await db.bad_deeds.aggregate(pipeline).to_list(7)
        
        # MongoDB dayOfWeek: 1=Sunday, 2=Monday, ..., 7=Saturday
        # Convert to more readable format
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_analysis = []
        
        for i in range(7):
            mongo_day = i + 1  # MongoDB uses 1-based indexing
            result = next((r for r in results if r["_id"] == mongo_day), None)
            
            if result:
                unique_dates = len(set(result["dates"]))
                avg_per_day = result["count"] / unique_dates if unique_dates > 0 else 0
            else:
                avg_per_day = 0
                result = {"count": 0}
            
            day_analysis.append({
                "day": day_names[i],
                "day_short": day_names[i][:3],
                "total_count": result["count"],
                "average_per_day": round(avg_per_day, 2)
            })
        
        # Find patterns
        max_day = max(day_analysis, key=lambda x: x["average_per_day"])
        min_day = min(day_analysis, key=lambda x: x["average_per_day"])
        
        insights = []
        if max_day["average_per_day"] > 0:
            insights.append(f"Your worst day is {max_day['day']} with an average of {max_day['average_per_day']} bad deeds")
        if min_day["average_per_day"] == 0:
            insights.append(f"You're consistently clean on {min_day['day']}s - great job!")
        elif max_day["average_per_day"] > min_day["average_per_day"] * 2:
            insights.append(f"You do {max_day['average_per_day']/min_day['average_per_day']:.1f}x more bad deeds on {max_day['day']}s than {min_day['day']}s")
        
        return {
            "day_analysis": day_analysis,
            "insights": insights,
            "analysis_period": f"{start_date.isoformat()} to {end_date.isoformat()}"
        }
    except Exception as e:
        logging.error(f"Error getting day-of-week analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get day-of-week analysis")

@api_router.get("/stats/streaks")
async def get_streak_analysis():
    """Get current and longest clean streaks"""
    try:
        # Get all days in the last 90 days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=89)
        
        # Get daily counts
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
        
        results = await db.bad_deeds.aggregate(pipeline).to_list(90)
        results_dict = {result["_id"]: result["count"] for result in results}
        
        # Create day-by-day analysis
        daily_data = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            count = results_dict.get(date_str, 0)
            daily_data.append({
                "date": date_str,
                "count": count,
                "is_clean": count == 0
            })
            current_date += timedelta(days=1)
        
        # Calculate streaks
        current_streak = 0
        longest_streak = 0
        current_streak_start = None
        longest_streak_period = None
        temp_streak_start = None
        temp_streak = 0
        
        # Calculate current streak (from today backwards)
        for i in range(len(daily_data) - 1, -1, -1):
            if daily_data[i]["is_clean"]:
                current_streak += 1
            else:
                break
        
        # Calculate longest streak
        for day in daily_data:
            if day["is_clean"]:
                if temp_streak == 0:
                    temp_streak_start = day["date"]
                temp_streak += 1
                
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
                    longest_streak_period = {
                        "start": temp_streak_start,
                        "end": day["date"],
                        "days": temp_streak
                    }
            else:
                temp_streak = 0
                temp_streak_start = None
        
        # Calculate current streak start date
        if current_streak > 0:
            current_streak_start = (end_date - timedelta(days=current_streak-1)).isoformat()
        
        return {
            "current_streak": {
                "days": current_streak,
                "start_date": current_streak_start,
                "status": "active" if current_streak > 0 else "broken"
            },
            "longest_streak": {
                "days": longest_streak,
                "period": longest_streak_period
            },
            "analysis_period": f"{start_date.isoformat()} to {end_date.isoformat()}"
        }
    except Exception as e:
        logging.error(f"Error getting streak analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get streak analysis")

@api_router.get("/stats/monthly")
async def get_monthly_stats(months: int = 12):
    """Get monthly statistics"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date.replace(day=1) - timedelta(days=30 * (months - 1))
        start_date = start_date.replace(day=1)  # First day of the start month
        
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
                            "format": "%Y-%m",
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
        
        results = await db.bad_deeds.aggregate(pipeline).to_list(months)
        results_dict = {result["_id"]: result["count"] for result in results}
        
        # Fill in missing months
        monthly_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            month_str = current_date.strftime("%Y-%m")
            count = results_dict.get(month_str, 0)
            
            monthly_stats.append({
                "month": month_str,
                "month_name": current_date.strftime("%B %Y"),
                "count": count
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculate trend
        if len(monthly_stats) >= 2:
            recent_avg = sum(stat["count"] for stat in monthly_stats[-3:]) / min(3, len(monthly_stats))
            older_avg = sum(stat["count"] for stat in monthly_stats[:-3][-3:]) / min(3, len(monthly_stats[:-3]))
            
            if older_avg > 0:
                trend_percentage = ((recent_avg - older_avg) / older_avg) * 100
                trend = "improving" if trend_percentage < -10 else "worsening" if trend_percentage > 10 else "stable"
            else:
                trend = "improving" if recent_avg == 0 else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "monthly_stats": monthly_stats,
            "trend": trend,
            "total_period": sum(stat["count"] for stat in monthly_stats)
        }
    except Exception as e:
        logging.error(f"Error getting monthly stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monthly stats")


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

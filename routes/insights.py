"""
Insights management endpoints
"""
from typing import List
from fastapi import APIRouter, HTTPException
from models.schemas import InsightResponse
from config import insights_collection
from utils.helpers import convert_objectid

router = APIRouter(prefix="/insights", tags=["insights"])

@router.get("/user/{user_id}", response_model=List[InsightResponse])
def get_user_insights(user_id: str, unread_only: bool = False):
    """Get insights for a user"""
    query = {"user_id": user_id}
    if unread_only:
        query["read"] = False
    
    insights = list(
        insights_collection.find(query)
        .sort("created_at", -1)
        .limit(20)
    )
    return [convert_objectid(insight) for insight in insights]

@router.put("/{insight_id}/read")
def mark_insight_read(insight_id: str):
    """Mark insight as read"""
    from utils.helpers import validate_objectid
    result = insights_collection.update_one(
        {"_id": validate_objectid(insight_id)},
        {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"status": "marked_as_read"}

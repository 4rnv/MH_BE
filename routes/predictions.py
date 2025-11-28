"""
ML Prediction endpoints
"""
from fastapi import APIRouter
from services.agent_service import AgentService

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("/risk/{user_id}")
def get_payment_risk(user_id: str):
    """
    Get ML-based risk prediction for user
    Returns probability of payment shortfall
    """
    return AgentService.predict_payment_risk(user_id)

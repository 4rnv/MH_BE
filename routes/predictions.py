"""
ML Prediction endpoints
"""
from fastapi import APIRouter, HTTPException
from services.agent_service import AgentService
from services.ml_service import ml_service

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("/risk/{user_id}")
def get_payment_risk(user_id: str):
    """
    Get ML-based risk prediction for user
    Returns probability of payment shortfall
    """
    return AgentService.predict_payment_risk(user_id)

@router.get("/income/{user_id}")
def get_income_prediction(user_id: str):
    """
    Get predicted income for next 7 days
    Returns weekly total, daily average, and confidence intervals
    
    Response example:
    {
        "predicted_weekly_total": 3200.50,
        "predicted_daily_avg": 457.21,
        "confidence_5th": 2240.35,  // Pessimistic scenario
        "confidence_50th": 3200.50,  // Most likely scenario
        "confidence_95th": 4160.65,  // Optimistic scenario
        "uncertainty": 0.25,
        "model_available": true
    }
    """
    try:
        prediction = ml_service.predict_weekly_income(user_id)
        return prediction
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate income prediction: {str(e)}"
        )
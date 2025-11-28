"""
Scheduled payment management endpoints
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from models.schemas import ScheduledPaymentModel, ScheduledPaymentResponse
from config import scheduled_payments_collection, users_collection
from utils.helpers import convert_objectid, validate_objectid

router = APIRouter(prefix="/scheduled_payments", tags=["scheduled_payments"])

@router.post("/", response_model=ScheduledPaymentResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_payment(payment: ScheduledPaymentModel):
    """Create a scheduled payment"""
    # Verify user exists
    user = users_collection.find_one({"_id": validate_objectid(payment.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    pay_dict = payment.model_dump()
    result = scheduled_payments_collection.insert_one(pay_dict)
    pay_dict["_id"] = str(result.inserted_id)
    return pay_dict

@router.get("/user/{user_id}", response_model=List[ScheduledPaymentResponse])
def get_user_scheduled_payments(user_id: str):
    """Get all scheduled payments for a user"""
    payments = list(scheduled_payments_collection.find({"user_id": user_id}))
    return [convert_objectid(pay) for pay in payments]

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_payment(payment_id: str):
    """Delete a scheduled payment"""
    result = scheduled_payments_collection.delete_one({"_id": validate_objectid(payment_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scheduled payment not found")

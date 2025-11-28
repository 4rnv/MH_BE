"""
Transaction management endpoints
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from pymongo import DESCENDING
from models.schemas import TransactionModel, TransactionResponse, TransactionType
from config import transactions_collection, virtual_accounts_collection
from utils.helpers import convert_objectid, validate_objectid
from services.agent_service import AgentService

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(transaction: TransactionModel):
    """Create a new transaction"""
    # Verify account exists
    account = virtual_accounts_collection.find_one({"_id": validate_objectid(transaction.acct_id)})
    if not account:
        raise HTTPException(status_code=404, detail="Virtual account not found")
    
    # Update account balance
    if transaction.type == TransactionType.deposit:
        virtual_accounts_collection.update_one(
            {"_id": validate_objectid(transaction.acct_id)},
            {"$inc": {"balance": transaction.amount}}
        )
    else:  # withdrawal
        if account["balance"] < transaction.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        virtual_accounts_collection.update_one(
            {"_id": validate_objectid(transaction.acct_id)},
            {"$inc": {"balance": -transaction.amount}}
        )
    
    tx_dict = transaction.model_dump()
    result = transactions_collection.insert_one(tx_dict)
    tx_dict["_id"] = str(result.inserted_id)

    user_id = account["user_id"]
    AgentService.check_balance_risk(user_id)

    return tx_dict

@router.get("/account/{acct_id}", response_model=List[TransactionResponse])
def get_account_transactions(acct_id: str, skip: int = 0, limit: int = 50):
    """Get all transactions for an account"""
    transactions = list(
        transactions_collection.find({"acct_id": acct_id})
        .sort("datetime", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    return [convert_objectid(tx) for tx in transactions]

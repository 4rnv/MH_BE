"""
Chat interface endpoints
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from config import virtual_accounts_collection, transactions_collection
from services.nlp_service import nlp_service
from services.agent_service import AgentService
from models.schemas import TransactionType, TransactionSource
from datetime import datetime, timezone

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    action_taken: bool
    transaction_id: str | None = None
    data: dict | None = None

@router.post("/message", response_model=ChatResponse)
async def process_chat_message(chat: ChatMessage):
    """
    Process a natural language message from the user.
    Detects intent -> Executes Action -> Returns Response
    """
    # 1. Analyze intent
    intent = nlp_service.extract_transaction_details(chat.message)
    
    if not intent:
        return ChatResponse(
            response="I couldn't understand the transaction details. Please try something like '180Rs for groceries'.",
            action_taken=False
        )
    
    # 2. Execute Action (Create Transaction)
    account = virtual_accounts_collection.find_one({"user_id": chat.user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Virtual account not found")
    
    acct_id = str(account["_id"])
    
    # Prepare transaction document
    tx_doc = {
        "acct_id": acct_id,
        "amount": intent.amount,
        "details": f"Chat entry: {intent.category}",
        "type": intent.type,  # deposit or withdrawal
        "merchant": intent.merchant or intent.category,
        "source": TransactionSource.chat.value,
        "datetime": datetime.now(timezone.utc).isoformat()
    }
    
    # Update balance logic
    if intent.type == "deposit":
        virtual_accounts_collection.update_one(
            {"_id": account["_id"]},
            {"$inc": {"balance": intent.amount}}
        )
    else:
        if account["balance"] < intent.amount:
             return ChatResponse(
                response=f"⚠️ Transaction failed! Insufficient balance. You have ₹{account['balance']} but tried to spend ₹{intent.amount}.",
                action_taken=False
            )
        virtual_accounts_collection.update_one(
            {"_id": account["_id"]},
            {"$inc": {"balance": -intent.amount}}
        )
    
    # Insert transaction
    result = transactions_collection.insert_one(tx_doc)
    
    # 3. Trigger Agentic Checks (Risk, Buffer, etc.)
    AgentService.check_balance_risk(chat.user_id)
    
    # 4. Formulate Response
    verb = "received" if intent.type == "deposit" else "spent"
    emoji = "💰" if intent.type == "deposit" else "💸"
    
    return ChatResponse(
        response=f"{emoji} recorded! You {verb} ₹{intent.amount} on {intent.category}.",
        action_taken=True,
        transaction_id=str(result.inserted_id),
        data=intent.model_dump()
    )

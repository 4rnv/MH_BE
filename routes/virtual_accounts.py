"""
Virtual account management endpoints
"""
from fastapi import APIRouter, HTTPException, status
from models.schemas import VirtualAccountModel, VirtualAccountResponse
from config import virtual_accounts_collection, users_collection
from utils.helpers import convert_objectid, validate_objectid

router = APIRouter(prefix="/virtual_accounts", tags=["virtual_accounts"])

@router.post("/", response_model=VirtualAccountResponse, status_code=status.HTTP_201_CREATED)
def create_virtual_account(account: VirtualAccountModel):
    """Create virtual account for a user"""
    # Verify user exists
    user = users_collection.find_one({"_id": validate_objectid(account.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if account already exists
    existing = virtual_accounts_collection.find_one({"user_id": account.user_id})
    if existing:
        raise HTTPException(status_code=400, detail="Virtual account already exists for this user")
    
    acct_dict = account.model_dump()
    result = virtual_accounts_collection.insert_one(acct_dict)
    acct_dict["_id"] = str(result.inserted_id)
    return acct_dict

@router.get("/user/{user_id}", response_model=VirtualAccountResponse)
def get_virtual_account(user_id: str):
    """Get virtual account for a user"""
    account = virtual_accounts_collection.find_one({"user_id": user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Virtual account not found")
    return convert_objectid(account)

@router.put("/{acct_id}", response_model=VirtualAccountResponse)
def update_virtual_account(acct_id: str, account: VirtualAccountModel):
    """Update virtual account balance/buffer"""
    result = virtual_accounts_collection.update_one(
        {"_id": validate_objectid(acct_id)},
        {"$set": account.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Virtual account not found")
    
    updated = virtual_accounts_collection.find_one({"_id": validate_objectid(acct_id)})
    return convert_objectid(updated)

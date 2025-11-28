"""
User management endpoints
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from models.schemas import UserModel, UserResponse
from config import users_collection
from utils.helpers import convert_objectid, validate_objectid

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserModel):
    """Create a new user"""
    user_dict = user.model_dump()
    
    # Check if user already exists
    existing = users_collection.find_one({"$or": [
        {"phone": user.phone},
        {"aadhaar": user.aadhaar}
    ]})
    if existing:
        raise HTTPException(status_code=400, detail="User with this phone or Aadhaar already exists")
    
    result = users_collection.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    return user_dict

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    """Get user by ID"""
    user = users_collection.find_one({"_id": validate_objectid(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return convert_objectid(user)

@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 10):
    """List all users with pagination"""
    users = list(users_collection.find().skip(skip).limit(limit))
    return [convert_objectid(user) for user in users]

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user: UserModel):
    """Update user information"""
    result = users_collection.update_one(
        {"_id": validate_objectid(user_id)},
        {"$set": user.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = users_collection.find_one({"_id": validate_objectid(user_id)})
    return convert_objectid(updated_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str):
    """Delete a user"""
    result = users_collection.delete_one({"_id": validate_objectid(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

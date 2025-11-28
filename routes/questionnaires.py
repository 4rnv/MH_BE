"""
Questionnaire management endpoints
"""
from fastapi import APIRouter, HTTPException, status
from models.schemas import QuestionnaireModel, QuestionnaireResponse
from config import questionnaires_collection, users_collection
from utils.helpers import convert_objectid, validate_objectid

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])

@router.post("/", response_model=QuestionnaireResponse, status_code=status.HTTP_201_CREATED)
def create_questionnaire(questionnaire: QuestionnaireModel):
    """Create questionnaire for a user"""
    # Verify user exists
    user = users_collection.find_one({"_id": validate_objectid(questionnaire.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    q_dict = questionnaire.model_dump()
    result = questionnaires_collection.insert_one(q_dict)
    q_dict["_id"] = str(result.inserted_id)
    return q_dict

@router.get("/user/{user_id}", response_model=QuestionnaireResponse)
def get_user_questionnaire(user_id: str):
    """Get questionnaire for a specific user"""
    questionnaire = questionnaires_collection.find_one({"user_id": user_id})
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return convert_objectid(questionnaire)

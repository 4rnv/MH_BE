"""
Pydantic models for request/response validation
"""
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================
class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"

class TransactionSource(str, Enum):
    UPI = "UPI"
    chat = "chat"
    bank_statement = "bank statement"

class Occurrence(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    annual = "annual"

class Importance(str, Enum):
    normal = "normal"
    high = "high"

# ============================================================================
# User Models
# ============================================================================
class UserModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    aadhaar: str = Field(..., pattern=r"^\d{12}$")
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    risk_level: RiskLevel = RiskLevel.medium
    language: str = Field(default="en", min_length=2, max_length=10)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rajesh Kumar",
                "aadhaar": "123456789012",
                "phone": "+919876543210",
                "risk_level": "medium",
                "language": "hi"
            }
        }

class UserResponse(UserModel):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

# ============================================================================
# Questionnaire Models
# ============================================================================
class QuestionnaireModel(BaseModel):
    user_id: str
    q1: str
    a1: str
    q2: str
    a2: str
    q3: str
    a3: str
    q4: str
    a4: str
    q5: str
    a5: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "q1": "What is your primary source of income?",
                "a1": "Food delivery",
                "q2": "How many dependents do you have?",
                "a2": "2",
                "q3": "What are your monthly fixed expenses?",
                "a3": "15000",
                "q4": "Do you have an emergency fund?",
                "a4": "No",
                "q5": "What is your savings goal?",
                "a5": "Festival expenses"
            }
        }

class QuestionnaireResponse(QuestionnaireModel):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

# ============================================================================
# Virtual Account Models
# ============================================================================
class VirtualAccountModel(BaseModel):
    user_id: str
    balance: float = Field(default=0.0, ge=0)
    buffer: float = Field(default=0.0, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "balance": 5000.50,
                "buffer": 1000.00
            }
        }

class VirtualAccountResponse(VirtualAccountModel):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

# ============================================================================
# Transaction Models
# ============================================================================
class TransactionModel(BaseModel):
    acct_id: str
    amount: float = Field(..., gt=0)
    details: Optional[str] = None
    type: TransactionType
    merchant: Optional[str] = None
    source: TransactionSource
    datetime: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "acct_id": "507f1f77bcf86cd799439011",
                "amount": 250.50,
                "details": "Swiggy delivery payment",
                "type": "deposit",
                "merchant": "Swiggy",
                "source": "UPI",
                "datetime": "2025-11-28T18:05:00Z"
            }
        }

class TransactionResponse(TransactionModel):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

# ============================================================================
# Scheduled Payment Models
# ============================================================================
class ScheduledPaymentModel(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0)
    occurrence: Occurrence
    particulars: str = Field(..., min_length=1)
    importance: Importance
    firstdate: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "amount": 6000.00,
                "occurrence": "monthly",
                "particulars": "Rent payment",
                "importance": "high",
                "firstdate": "2025-12-01"
            }
        }

class ScheduledPaymentResponse(ScheduledPaymentModel):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class InsightType(str, Enum):
    low_balance_warning = "low_balance_warning"
    buffer_breach = "buffer_breach"
    payment_due_soon = "payment_due_soon"
    income_volatility_alert = "income_volatility_alert"
    savings_opportunity = "savings_opportunity"

class InsightPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class InsightModel(BaseModel):
    user_id: str
    type: InsightType
    priority: InsightPriority
    title: str
    message: str
    action_suggestion: Optional[str] = None
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class InsightResponse(InsightModel):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True
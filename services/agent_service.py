"""
Agentic AI services for SafeBalance
Handles buffer calculation, risk detection, and insight generation
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from config import (
    virtual_accounts_collection, 
    scheduled_payments_collection,
    insights_collection,
    users_collection
)
from models.schemas import InsightType, InsightPriority, Occurrence
from bson import ObjectId
from services.ml_service import ml_service

class AgentService:
    
    @staticmethod
    def calculate_weekly_buffer(user_id: str) -> float:
        """
        Calculate the buffer needed for next 7 days based on scheduled payments
        """
        scheduled_payments = list(scheduled_payments_collection.find({"user_id": user_id}))
        
        today = datetime.now(timezone.utc)
        weekly_expenses = 0.0
        
        for payment in scheduled_payments:
            first_date = datetime.fromisoformat(payment["firstdate"])
            occurrence = payment["occurrence"]
            amount = payment["amount"]
            
            # Check if payment falls in next 7 days
            if occurrence == Occurrence.weekly.value:
                # Weekly payments - definitely included
                weekly_expenses += amount
            elif occurrence == Occurrence.monthly.value:
                # Check if payment day is in next 7 days
                days_until_payment = (first_date.day - today.day) % 30
                if 0 <= days_until_payment <= 7:
                    weekly_expenses += amount
            elif occurrence == Occurrence.annual.value:
                # Check if annual payment is due in next 7 days
                this_year_date = first_date.replace(year=today.year)
                days_diff = (this_year_date - today).days
                if 0 <= days_diff <= 7:
                    weekly_expenses += amount
        
        return round(weekly_expenses, 2)

    @staticmethod
    def predict_payment_risk(user_id: str) -> Dict:
        """
        AGENTIC AI: Predict risk of missing payments using ML model
        
        Logic:
        1. Get current balance
        2. Calculate next week's expenses (buffer)
        3. Predict next week's income using Random Forest
        4. Calculate probability of shortfall
        5. Generate insight if risk is above threshold
        """
        # Get user's virtual account
        account = virtual_accounts_collection.find_one({"user_id": user_id})
        if not account:
            return {"error": "Account not found"}
        
        current_balance = account["balance"]
        weekly_expenses = AgentService.calculate_weekly_buffer(user_id)
        
        # Get ML prediction for next week's income
        income_prediction = ml_service.predict_weekly_income(user_id)
        
        predicted_income_pessimistic = income_prediction['confidence_5th']
        predicted_income_median = income_prediction['confidence_50th']
        predicted_income_optimistic = income_prediction['confidence_95th']
        
        # Calculate projected balance at end of week
        projected_balance_pessimistic = current_balance + predicted_income_pessimistic - weekly_expenses
        projected_balance_median = current_balance + predicted_income_median - weekly_expenses
        projected_balance_optimistic = current_balance + predicted_income_optimistic - weekly_expenses
        
        # Calculate risk probability based on scenarios
        uncertainty = income_prediction['uncertainty']
        
        if projected_balance_pessimistic < 0:
            # High risk - even pessimistic income won't cover expenses
            risk_probability = 0.85 + (uncertainty * 0.15)  # 85-100% risk
            risk_level = "critical"
        elif projected_balance_median < 0:
            # Medium-high risk - median scenario shows shortfall
            risk_probability = 0.60 + (uncertainty * 0.25)  # 60-85% risk
            risk_level = "high"
        elif projected_balance_median < weekly_expenses * 0.5:
            # Medium risk - balance will be low
            risk_probability = 0.35 + (uncertainty * 0.25)  # 35-60% risk
            risk_level = "medium"
        elif projected_balance_optimistic < weekly_expenses:
            # Low-medium risk
            risk_probability = 0.15 + (uncertainty * 0.20)  # 15-35% risk
            risk_level = "low"
        else:
            # Low risk - even optimistic scenario is safe
            risk_probability = 0.05 + (uncertainty * 0.10)  # 5-15% risk
            risk_level = "minimal"
        
        risk_probability = min(0.99, risk_probability)  # Cap at 99%
        
        result = {
            "user_id": user_id,
            "current_balance": current_balance,
            "weekly_expenses": weekly_expenses,
            "predicted_income_range": {
                "pessimistic": predicted_income_pessimistic,
                "median": predicted_income_median,
                "optimistic": predicted_income_optimistic
            },
            "projected_balance_range": {
                "pessimistic": round(projected_balance_pessimistic, 2),
                "median": round(projected_balance_median, 2),
                "optimistic": round(projected_balance_optimistic, 2)
            },
            "risk_probability": round(risk_probability, 2),
            "risk_level": risk_level,
            "model_uncertainty": uncertainty,
            "model_available": income_prediction['model_available']
        }
        
        # Generate insight if risk is above threshold (35%)
        if risk_probability >= 0.35:
            AgentService._generate_risk_insight(user_id, result)
        
        return result
    
    @staticmethod
    def _generate_risk_insight(user_id: str, risk_data: Dict):
        """Generate an insight based on risk prediction"""
        
        risk_prob = risk_data["risk_probability"]
        risk_level = risk_data["risk_level"]
        current_balance = risk_data["current_balance"]
        weekly_expenses = risk_data["weekly_expenses"]
        shortage = weekly_expenses - current_balance - risk_data["predicted_income_range"]["pessimistic"]
        
        # Check if similar insight exists in last 24 hours (avoid spam)
        recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        existing = insights_collection.find_one({
            "user_id": user_id,
            "type": InsightType.income_volatility_alert.value,
            "created_at": {"$gte": recent_cutoff}
        })
        
        if existing:
            return  # Don't spam
        
        # Determine priority and message based on risk level
        if risk_level == "critical":
            priority = InsightPriority.critical
            title = "🚨 Critical: High Risk of Payment Shortfall"
            message = (
                f"There is a {int(risk_prob * 100)}% chance you won't be able to cover next week's "
                f"expenses (₹{weekly_expenses:.2f}). Your current balance is ₹{current_balance:.2f} "
                f"and predicted income may be insufficient."
            )
            action = (
                f"URGENT: Avoid all non-essential spending this week. "
                f"Try to earn an additional ₹{abs(shortage):.2f} or postpone ₹{abs(shortage):.2f} in expenses."
            )
        elif risk_level == "high":
            priority = InsightPriority.high
            title = "⚠️ Warning: Moderate Risk of Payment Issues"
            message = (
                f"There is a {int(risk_prob * 100)}% chance of facing payment difficulties next week. "
                f"Your expenses (₹{weekly_expenses:.2f}) may exceed available funds."
            )
            action = (
                f"Recommended: Limit discretionary spending to essentials only. "
                f"Consider picking up extra work if possible."
            )
        else:  # medium
            priority = InsightPriority.medium
            title = "💡 Advisory: Monitor Your Spending"
            message = (
                f"There is a {int(risk_prob * 100)}% chance of a tight budget next week. "
                f"Your predicted income may be lower than usual."
            )
            action = (
                "Be mindful of unnecessary expenses. Save where you can to maintain your buffer."
            )
        
        # Create insight
        insight = {
            "user_id": user_id,
            "type": InsightType.income_volatility_alert.value,
            "priority": priority.value,
            "title": title,
            "message": message,
            "action_suggestion": action,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "risk_probability": risk_prob,
                "risk_level": risk_level,
                "predicted_income_median": risk_data["predicted_income_range"]["median"],
                "weekly_expenses": weekly_expenses
            }
        }
        
        insights_collection.insert_one(insight)
        print(f"Generated ML-based risk insight for user {user_id} ({int(risk_prob*100)}% risk)")

    @staticmethod
    def update_buffer_for_user(user_id: str) -> Dict:
        """
        Recalculate and update the buffer for a user's virtual account
        """
        new_buffer = AgentService.calculate_weekly_buffer(user_id)
        
        result = virtual_accounts_collection.update_one(
            {"user_id": user_id},
            {"$set": {"buffer": new_buffer}}
        )
        
        return {
            "user_id": user_id,
            "new_buffer": new_buffer,
            "updated": result.modified_count > 0
        }
    
    @staticmethod
    def check_balance_risk(user_id: str) -> None:
        """
        Check if balance is below buffer and generate insights
        """
        account = virtual_accounts_collection.find_one({"user_id": user_id})
        if not account:
            return
        
        balance = account["balance"]
        buffer = account["buffer"]
        
        # Check if already has recent similar insight (avoid spam)
        recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        existing_insight = insights_collection.find_one({
            "user_id": user_id,
            "type": InsightType.buffer_breach.value,
            "created_at": {"$gte": recent_cutoff}
        })
        
        if existing_insight:
            return  # Don't spam user with same insight
        
        # Risk levels
        if balance < buffer * 0.5:  # Balance less than 50% of buffer
            priority = InsightPriority.critical
            title = "🚨 Critical: Balance Very Low"
            message = f"Your balance (₹{balance:.2f}) is critically low. You need ₹{buffer:.2f} for next week's expenses."
            action = f"Add ₹{(buffer - balance):.2f} to your account immediately or postpone non-essential payments."
            
        elif balance < buffer:  # Balance less than buffer
            priority = InsightPriority.high
            title = "⚠️ Warning: Balance Below Buffer"
            message = f"Your balance (₹{balance:.2f}) is below your weekly buffer (₹{buffer:.2f})."
            action = f"Consider moving ₹{(buffer - balance):.2f} to your account to cover upcoming expenses."
            
        elif balance < buffer * 1.5:  # Balance is close to buffer
            priority = InsightPriority.medium
            title = "💡 Advisory: Monitor Your Balance"
            message = f"Your balance (₹{balance:.2f}) is close to your buffer threshold (₹{buffer:.2f})."
            action = "Be mindful of spending this week to maintain a healthy buffer."
            
        else:
            return  # Balance is healthy, no insight needed
        
        # Create insight
        insight = {
            "user_id": user_id,
            "type": InsightType.buffer_breach.value,
            "priority": priority.value,
            "title": title,
            "message": message,
            "action_suggestion": action,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        insights_collection.insert_one(insight)
        print(f"Generated {priority.value} insight for user {user_id}")
    
    @staticmethod
    def check_upcoming_payments(user_id: str) -> None:
        """
        Check for payments due in next 3 days and generate reminders
        """
        scheduled_payments = list(scheduled_payments_collection.find({
            "user_id": user_id,
            "importance": "high"
        }))
        
        today = datetime.now(timezone.utc)
        
        for payment in scheduled_payments:
            first_date = datetime.fromisoformat(payment["firstdate"])
            occurrence = payment["occurrence"]
            
            # Calculate days until payment
            if occurrence == Occurrence.monthly.value:
                days_until = (first_date.day - today.day) % 30
            elif occurrence == Occurrence.weekly.value:
                days_until = (first_date.weekday() - today.weekday()) % 7
            else:
                continue
            
            # Generate reminder if due in 1-3 days
            if 1 <= days_until <= 3:
                # Check if already reminded
                recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
                existing = insights_collection.find_one({
                    "user_id": user_id,
                    "type": InsightType.payment_due_soon.value,
                    "message": {"$regex": payment["particulars"]},
                    "created_at": {"$gte": recent_cutoff}
                })
                
                if existing:
                    continue
                
                insight = {
                    "user_id": user_id,
                    "type": InsightType.payment_due_soon.value,
                    "priority": InsightPriority.high.value,
                    "title": f"Payment Due: {payment['particulars']}",
                    "message": f"Your {payment['particulars']} payment of ₹{payment['amount']:.2f} is due in {days_until} day(s).",
                    "action_suggestion": f"Ensure ₹{payment['amount']:.2f} is available in your account.",
                    "read": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                insights_collection.insert_one(insight)
                print(f"Payment reminder created for {payment['particulars']}")

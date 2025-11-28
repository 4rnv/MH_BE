import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List
import os

class MLPredictionService:
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.feature_columns = None
        self.model_loaded = False
        self.load_model()
    
    def load_model(self):
        """Load the trained Random Forest model from Google Drive or local path"""
        try:
            # Update these paths to where you saved your model
            model_path = os.getenv('MODEL_PATH', './model/income_volatility_7day_model.pkl')
            encoder_path = os.getenv('ENCODER_PATH', './model/archetype_encoder.pkl')
            config_path = os.getenv('CONFIG_PATH', './model/model_config_7day.json')
            
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            with open(encoder_path, 'rb') as f:
                self.label_encoder = pickle.load(f)
            
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.feature_columns = config['feature_columns']
            
            self.model_loaded = True
            print("ML model loaded successfully")
            
        except Exception as e:
            print(f"Failed to load ML model: {e}")
            print("Model predictions will be unavailable")
            self.model_loaded = False
    
    def get_user_archetype(self, user_id: str) -> str:
        """Determine user archetype from questionnaire or transaction patterns"""
        from config import questionnaires_collection
        
        questionnaire = questionnaires_collection.find_one({"user_id": user_id})
        if questionnaire and questionnaire.get('a1'):
            income_source = questionnaire['a1'].lower()
            if 'delivery' in income_source or 'swiggy' in income_source or 'zomato' in income_source:
                return 'food_delivery_rider'
            elif 'cab' in income_source or 'uber' in income_source or 'ola' in income_source:
                return 'cab_driver'
            elif 'freelanc' in income_source or 'design' in income_source:
                return 'freelancer'
            elif 'labor' in income_source or 'construction' in income_source:
                return 'part_time_laborer'
            elif 'shop' in income_source or 'retail' in income_source:
                return 'shop_assistant'
        
        return 'food_delivery_rider'  # Default
    
    def prepare_features(self, user_id: str, transactions: List[Dict]) -> pd.DataFrame:
        """Prepare features for prediction from user's transaction history"""
        from config import transactions_collection, virtual_accounts_collection
        
        if not transactions:
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            account = virtual_accounts_collection.find_one({"user_id": user_id})
            if account:
                acct_id = str(account["_id"])
                transactions = list(transactions_collection.find({
                    "acct_id": acct_id,
                    "type": "deposit",
                    "datetime": {"$gte": thirty_days_ago}
                }).sort("datetime", -1))
        
        archetype = self.get_user_archetype(user_id)
        archetype_encoded = list(self.label_encoder.classes_).index(archetype)
        
        now = datetime.now(timezone.utc)
        
        # Calculate rolling statistics
        if len(transactions) > 0:
            amounts = [t['amount'] for t in transactions[-30:]]
            income_lag_1 = amounts[0] if len(amounts) > 0 else 0
            income_lag_3 = amounts[2] if len(amounts) > 2 else income_lag_1
            income_lag_7 = amounts[6] if len(amounts) > 6 else income_lag_1
            
            recent_7 = amounts[:7] if len(amounts) >= 7 else amounts
            recent_14 = amounts[:14] if len(amounts) >= 14 else amounts
            
            income_rolling_mean_7 = np.mean(recent_7) if recent_7 else 0
            income_rolling_std_7 = np.std(recent_7) if len(recent_7) > 1 else 0
            income_rolling_max_7 = np.max(recent_7) if recent_7 else 0
            income_rolling_min_7 = np.min(recent_7) if recent_7 else 0
            
            income_rolling_mean_14 = np.mean(recent_14) if recent_14 else income_rolling_mean_7
            income_rolling_std_14 = np.std(recent_14) if len(recent_14) > 1 else income_rolling_std_7
            
            income_cv_7 = income_rolling_std_7 / (income_rolling_mean_7 + 1e-6)
            zero_income_count_7 = sum(1 for a in recent_7 if a == 0)
        else:
            income_lag_1 = income_lag_3 = income_lag_7 = 0
            income_rolling_mean_7 = income_rolling_std_7 = 0
            income_rolling_max_7 = income_rolling_min_7 = 0
            income_rolling_mean_14 = income_rolling_std_14 = 0
            income_cv_7 = 0
            zero_income_count_7 = 0
        
        features = {
            'archetype_encoded': archetype_encoded,
            'day_of_week': now.weekday(),
            'month': now.month,
            'week_of_year': now.isocalendar()[1],
            'is_weekend': 1 if now.weekday() >= 5 else 0,
            'is_festival': 0,
            'is_monsoon': 1 if now.month in [6, 7, 8, 9] else 0,
            'is_month_start': 1 if now.day <= 7 else 0,
            'is_month_end': 1 if now.day >= 24 else 0,
            'income_lag_1': income_lag_1,
            'income_lag_3': income_lag_3,
            'income_lag_7': income_lag_7,
            'income_rolling_mean_7': income_rolling_mean_7,
            'income_rolling_std_7': income_rolling_std_7,
            'income_rolling_max_7': income_rolling_max_7,
            'income_rolling_min_7': income_rolling_min_7,
            'income_rolling_mean_14': income_rolling_mean_14,
            'income_rolling_std_14': income_rolling_std_14,
            'income_cv_7': income_cv_7,
            'zero_income_count_7': zero_income_count_7
        }
        
        df = pd.DataFrame([features])
        return df[self.feature_columns]
    
    def predict_weekly_income(self, user_id: str, transactions: List[Dict] = None) -> Dict:
        """
        Predict average daily income for next 7 days
        Returns confidence intervals and uncertainty
        """
        if not self.model_loaded:
            # Fallback prediction
            from config import transactions_collection, virtual_accounts_collection
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            account = virtual_accounts_collection.find_one({"user_id": user_id})
            if account:
                acct_id = str(account["_id"])
                recent_txs = list(transactions_collection.find({
                    "acct_id": acct_id,
                    "type": "deposit",
                    "datetime": {"$gte": thirty_days_ago}
                }))
                if recent_txs:
                    daily_avg = np.mean([t['amount'] for t in recent_txs])
                    weekly_total = daily_avg * 7
                    return {
                        'predicted_weekly_total': weekly_total,
                        'predicted_daily_avg': daily_avg,
                        'confidence_5th': weekly_total * 0.7,
                        'confidence_50th': weekly_total,
                        'confidence_95th': weekly_total * 1.3,
                        'uncertainty': 0.3,
                        'model_available': False
                    }
            
            return {
                'predicted_weekly_total': 3000,
                'predicted_daily_avg': 428,
                'confidence_5th': 2100,
                'confidence_50th': 3000,
                'confidence_95th': 3900,
                'uncertainty': 0.3,
                'model_available': False
            }
        
        try:
            features = self.prepare_features(user_id, transactions)
            
            # Get predictions from all trees
            tree_predictions = []
            for tree in self.model.estimators_:
                tree_pred = tree.predict(features)[0]
                tree_predictions.append(tree_pred)
            
            tree_predictions = np.array(tree_predictions)
            
            predicted_daily_avg = np.mean(tree_predictions)
            predicted_weekly_total = predicted_daily_avg * 7
            
            confidence_5th = np.percentile(tree_predictions, 5) * 7
            confidence_50th = np.percentile(tree_predictions, 50) * 7
            confidence_95th = np.percentile(tree_predictions, 95) * 7
            
            uncertainty = np.std(tree_predictions) / (np.mean(tree_predictions) + 1e-6)
            
            return {
                'predicted_weekly_total': round(predicted_weekly_total, 2),
                'predicted_daily_avg': round(predicted_daily_avg, 2),
                'confidence_5th': round(confidence_5th, 2),
                'confidence_50th': round(confidence_50th, 2),
                'confidence_95th': round(confidence_95th, 2),
                'uncertainty': round(uncertainty, 3),
                'model_available': True
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                'predicted_weekly_total': 3000,
                'predicted_daily_avg': 428,
                'confidence_5th': 2100,
                'confidence_50th': 3000,
                'confidence_95th': 3900,
                'uncertainty': 0.3,
                'model_available': False,
                'error': str(e)
            }

# Singleton instance
ml_service = MLPredictionService()

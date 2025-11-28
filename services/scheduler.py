"""
Background scheduler for periodic agent tasks
"""
import schedule
import time
from threading import Thread
from config import users_collection
from services.agent_service import AgentService

def update_all_buffers():
    """Update buffers for all users"""
    users = users_collection.find({})
    for user in users:
        user_id = str(user["_id"])
        try:
            AgentService.update_buffer_for_user(user_id)
            AgentService.check_balance_risk(user_id)
            AgentService.check_upcoming_payments(user_id)
            print(f"Updated agent checks for user {user_id}")
        except Exception as e:
            print(f"Error updating user {user_id}: {e}")

def run_scheduler():
    """Run scheduled tasks in background thread"""
    # Update buffers daily at midnight
    schedule.every().day.at("00:00").do(update_all_buffers)
    
    # Check payment reminders every 6 hours
    schedule.every(6).hours.do(lambda: [
        AgentService.check_upcoming_payments(str(u["_id"])) 
        for u in users_collection.find({})
    ])
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def start_background_tasks():
    """Start background scheduler in separate thread"""
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background scheduler started")

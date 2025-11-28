from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import create_indexes
from routes import users, questionnaires, virtual_accounts, transactions, scheduled_payments, insights, predictions
from services.scheduler import start_background_tasks

# Create database indexes on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load environment variables and create indexes
    create_indexes()
    start_background_tasks()
    yield
    # Shutdown: Clean up resources (if needed)

app = FastAPI(
    title="SafeBalance API",
    description="Financial management platform for variable income workers",
    version="1.0.0",
    lifespan=lifespan
)    
# Include routers
app.include_router(users.router)
app.include_router(questionnaires.router)
app.include_router(virtual_accounts.router)
app.include_router(transactions.router)
app.include_router(scheduled_payments.router)
app.include_router(insights.router)
app.include_router(predictions.router)

# Health check endpoint
@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SafeBalance API",
        "version": "1.0.0"
    }

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

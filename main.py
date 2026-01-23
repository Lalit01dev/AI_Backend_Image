import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import campaign
from dotenv import load_dotenv
import os
from app.services.file_cleanup import file_cleanup_service
from app.database import Base, engine


load_dotenv()



def safe_print(*args):
    for a in args:
        if isinstance(a, (bytes, bytearray)):
            print("[BINARY DATA OMITTED]")
            return
    print(*args)

from fastapi import FastAPI
# all other imports below


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Commercial Video Generator API",
    description="AI-powered video ad campaign generator",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(campaign.router)

@app.get("/")
async def root():
    return {
        "message": "Commercial Video Generator API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
        reload=True
    )

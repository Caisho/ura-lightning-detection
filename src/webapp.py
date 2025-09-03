"""
Lightning Detection Web Application

A FastAPI-based web app that displays real-time Singapore lightning strikes
on an interactive map with refresh functionality.
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from datetime import datetime
import json
import os

from .lightning_service import lightning_service
from .map_generator import map_generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Singapore Lightning Detection",
    description="Real-time lightning strike monitoring for Singapore",
    version="1.0.0"
)

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Create directories if they don't exist
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global cache for lightning data (in production, use Redis or similar)
lightning_cache = {
    "last_update": None,
    "data": None,
    "map_html": None
}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page showing the lightning map."""
    try:
        # Get initial lightning data
        lightning_data = lightning_service.get_lightning_summary()
        
        # Update cache
        lightning_cache["last_update"] = datetime.now().isoformat()
        lightning_cache["data"] = lightning_data
        
        # Generate map HTML
        if lightning_data["success"]:
            map_html = map_generator.create_singapore_map(lightning_data["coordinates"])
            lightning_cache["map_html"] = map_html
        else:
            map_html = map_generator.create_singapore_map([])
            lightning_cache["map_html"] = map_html
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "lightning_data": lightning_data,
            "map_html": map_html,
            "last_update": lightning_cache["last_update"]
        })
    
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        # Return error page
        error_data = {
            "success": False,
            "error": str(e),
            "coordinates": [],
            "total_strikes": 0
        }
        error_map = map_generator.create_singapore_map([])
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "lightning_data": error_data,
            "map_html": error_map,
            "last_update": datetime.now().isoformat(),
            "error": str(e)
        })


@app.get("/api/lightning", response_class=JSONResponse)
async def get_lightning_data():
    """API endpoint to get current lightning data as JSON."""
    try:
        lightning_data = lightning_service.get_lightning_summary()
        return JSONResponse(content=lightning_data)
    except Exception as e:
        logger.error(f"Error in lightning API: {e}")
        return JSONResponse(
            content={
                "success": False,
                "error": str(e),
                "coordinates": [],
                "total_strikes": 0,
                "timestamp": datetime.now().isoformat()
            },
            status_code=500
        )


@app.get("/api/refresh", response_class=JSONResponse)
async def refresh_lightning_data():
    """API endpoint to refresh lightning data and return updated information."""
    try:
        # Fetch fresh lightning data
        lightning_data = lightning_service.get_lightning_summary()
        
        # Update cache
        lightning_cache["last_update"] = datetime.now().isoformat()
        lightning_cache["data"] = lightning_data
        
        # Generate new map HTML
        if lightning_data["success"]:
            map_html = map_generator.create_singapore_map(lightning_data["coordinates"])
            lightning_cache["map_html"] = map_html
        else:
            map_html = map_generator.create_singapore_map([])
            lightning_cache["map_html"] = map_html
        
        return JSONResponse(content={
            "success": True,
            "lightning_data": lightning_data,
            "map_html": map_html,
            "last_update": lightning_cache["last_update"]
        })
    
    except Exception as e:
        logger.error(f"Error refreshing lightning data: {e}")
        return JSONResponse(
            content={
                "success": False,
                "error": str(e),
                "last_update": datetime.now().isoformat()
            },
            status_code=500
        )


@app.get("/api/status")
async def get_status():
    """API endpoint to get application status and health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "last_update": lightning_cache.get("last_update"),
        "has_cached_data": lightning_cache.get("data") is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/map-only", response_class=HTMLResponse)
async def map_only():
    """Endpoint that returns just the map HTML for embedding."""
    try:
        if lightning_cache.get("map_html"):
            return HTMLResponse(content=lightning_cache["map_html"])
        else:
            # Generate fresh map
            lightning_data = lightning_service.get_lightning_summary()
            map_html = map_generator.create_singapore_map(
                lightning_data.get("coordinates", [])
            )
            return HTMLResponse(content=map_html)
    except Exception as e:
        logger.error(f"Error in map-only route: {e}")
        # Return basic map
        basic_map = map_generator.create_singapore_map([])
        return HTMLResponse(content=basic_map)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Singapore Lightning Detection Web App...")
    logger.info("Access the application at: http://localhost:8000")
    logger.info("API endpoints:")
    logger.info("  - GET /api/lightning - Get lightning data as JSON")
    logger.info("  - GET /api/refresh - Refresh and get updated lightning data")
    logger.info("  - GET /api/status - Get application status")
    logger.info("  - GET /health - Health check")
    
    uvicorn.run(
        "src.webapp:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
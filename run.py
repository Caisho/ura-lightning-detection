#!/usr/bin/env python3
"""
Simple startup script for the Lightning Detection Web App
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from src.webapp import app
    
    print("🌩️ Starting Singapore Lightning Detection Web App...")
    print("📡 API: NEA Lightning Alert API")
    print("🌐 Server: http://localhost:8000")
    print("📍 Map: Interactive Singapore lightning strikes")
    print("🔄 Auto-refresh: Every 5 minutes")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
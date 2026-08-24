import os
import sys
import uvicorn

if __name__ == "__main__":
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        port = 8000
    
    print(f"ParcelPilot Agent starting on 0.0.0.0:{port} (PID: {os.getpid()})...", flush=True)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, log_level="info")

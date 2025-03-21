#!/bin/bash

# Start the revenue service
PORT=8001 pdm run uvicorn app:app --host 0.0.0.0 --port 8001 &

# Start the rebates service
PORT=8002 pdm run uvicorn app:app --host 0.0.0.0 --port 8002 &

# Start the specialty service
PORT=8003 pdm run uvicorn app:app --host 0.0.0.0 --port 8003 &

# Wait for all background processes
wait 
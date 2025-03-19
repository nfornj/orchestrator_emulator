FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY start.sh .

# Make the start script executable
RUN chmod +x start.sh

# Expose the ports
EXPOSE 8001 8002 8003

# Command to run the mock services
CMD ["./start.sh"] 
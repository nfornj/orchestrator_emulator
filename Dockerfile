FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with more verbose output
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    librdkafka-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies with verbose output
COPY requirements.txt .
RUN pip install --no-cache-dir --verbose -r requirements.txt

# Verify confluent-kafka installation
RUN pip list | grep confluent-kafka || (echo "confluent-kafka installation failed" && exit 1)

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
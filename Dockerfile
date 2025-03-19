FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    librdkafka-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PDM
RUN pip install --no-cache-dir pdm

# Copy only pyproject.toml and pdm.lock first for better layer caching
COPY pyproject.toml pdm.lock* ./

# Install dependencies with PDM
RUN pdm config python.use_venv false && \
    pdm install --no-self --no-editable --prod

# Create some required directories
RUN mkdir -p __pypackages__/3.12/lib

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Set PATH to use PDM's installed packages
ENV PYTHONPATH=/app:/app/__pypackages__/3.12/lib
ENV PATH="/app/__pypackages__/3.12/bin:$PATH"

# Verify confluent-kafka installation (as a sanity check)
RUN pdm run python -c "import confluent_kafka; print(f'confluent-kafka {confluent_kafka.__version__} successfully installed')"

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
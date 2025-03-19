FROM python:3.12-slim

WORKDIR /app

# Install PDM
RUN pip install --no-cache-dir pdm

# Copy pyproject.toml file
COPY pyproject.toml .
COPY pdm.lock* ./

# Install dependencies with PDM
RUN pdm config python.use_venv false && \
    pdm install --no-self --no-editable --prod

# Create required directories
RUN mkdir -p __pypackages__/3.12/lib

# Copy application code
COPY app.py .
COPY start.sh .

# Make the start script executable
RUN chmod +x start.sh

# Set PATH to use PDM's installed packages
ENV PYTHONPATH=/app:/app/__pypackages__/3.12/lib
ENV PATH="/app/__pypackages__/3.12/bin:$PATH"

# Expose the ports
EXPOSE 8001 8002 8003

# Command to run the mock services
CMD ["./start.sh"] 
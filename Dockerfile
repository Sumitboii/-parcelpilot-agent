# Multi-stage / lightweight Python 3.11 container for ParcelPilot Agent
FROM python:3.11-slim

# Force cache-bust: update this timestamp to invalidate Railway's snapshot cache
ARG CACHE_BUST=2026-08-24-v5

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer model weights to cache them in the Docker image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application files
COPY backend/ ./backend/
COPY sources/ ./sources/
COPY frontend/ ./frontend/
COPY showcase/ ./showcase/
COPY PRODUCT_SHOWCASE.html .
COPY start.py .
COPY .env.example .
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Start application via Python runner
CMD ["python", "start.py"]



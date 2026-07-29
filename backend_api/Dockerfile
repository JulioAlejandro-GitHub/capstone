# Backend Dockerfile for Machine Learning Pipeline & FastAPI
# We use Python 3.12-slim to keep the base image lightweight while supporting modern Python features.
FROM python:3.12-slim

# Set environment variables for non-interactive installations and Python optimizations
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# Requires libgl1-mesa-glx and libglib2.0-0 for OpenCV and general vision tasks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from both the ML project and the backend API
COPY backend_api/requirements.txt /app/backend_requirements.txt
COPY malaria_dl_local_project/requirements.txt /app/ml_requirements.txt

# Optimizing ML libraries installation and standardizing dependencies
# We use --no-cache-dir to avoid bloated image sizes.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/ml_requirements.txt -r /app/backend_requirements.txt

# Create necessary directories for local application functioning and run under a non-root user for security
RUN addgroup --system capstone && adduser --system --ingroup capstone capstone
RUN mkdir -p /app/var/storage /app/var/artifacts && chown -R capstone:capstone /app

# Copy the ML source files
# First we copy the entire ML project since it contains necessary modules to be imported
COPY malaria_dl_local_project /app/malaria_dl_local_project
ENV PYTHONPATH="/app/malaria_dl_local_project:/app"

# Copy the backend API files
COPY backend_api/app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Fix ownership
RUN chown -R capstone:capstone /app

# Use non-root user
USER capstone

EXPOSE 8000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

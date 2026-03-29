# Use official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables to prevent Python from writing pyc files and prevent buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/app:/app/Backend/services/backend"

# Set the working directory to /app
WORKDIR /app

# Install system dependencies required for pdfplumber and casparser (and python build libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements files
COPY requirements.txt /app/requirements.txt
COPY Backend/services/backend/requirements.txt /app/backend-requirements.txt

# Install CPU-Only PyTorch first to prevent strict Resource Exhaustion (OOM killer)
# Default pip pulls 3GB of Nvidia libraries which instantly kills standard cloud builders
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install python dependencies from both lists
# (Ignoring versions to get latest pydantic resolution if there are mild conflicts)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/backend-requirements.txt

# Install casparser without dependencies to prevent pdfminer version looping errors
RUN pip install --no-cache-dir casparser==0.8.1 --no-deps

# Install python-multipart explicitly for form-data (Form16/CAS upload handling)
RUN pip install --no-cache-dir python-multipart

# Copy the entire project code into the container
COPY . /app/

# Expose port (DigitalOcean uses 8080 by default, which can be configured via environment)
EXPOSE 8080

# Command to run the FastApi app via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

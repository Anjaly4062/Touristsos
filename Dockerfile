# ==============================================================================
# Dockerfile for Tourist SOS Dashboard (Django Backend)
# ==============================================================================

# Official lightweight Python 3.12 image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for mysqlclient, Pillow, and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to take advantage of Docker cache layers
COPY requirements.txt /app/

# Upgrade pip and install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . /app/

# Expose port 8000 for web traffic
EXPOSE 8000

# Default command to start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


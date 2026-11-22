FROM python:3.14-slim

# Install system dependencies needed to compile mysqlclient and run healthchecks (curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages using requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy storage code and specifications into the container
COPY . /app

# Document internal port
EXPOSE 8090

# Launch storage service
CMD ["uvicorn", "storage:app", "--host", "0.0.0.0", "--port", "8090"]

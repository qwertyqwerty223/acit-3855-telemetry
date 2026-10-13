FROM python:3.14-slim

# Install system dependencies needed to compile mysqlclient and run healthchecks (curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages needed by the storage service
RUN pip install connexion[flask] connexion[uvicorn] connexion[swagger-ui] sqlalchemy mysqlclient pyyaml

# Copy storage code and specifications into the container
COPY . /app

# Document internal port
EXPOSE 8090

# Launch storage service
CMD ["uvicorn", "storage:app", "--host", "0.0.0.0", "--port", "8090"]
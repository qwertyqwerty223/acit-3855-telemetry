FROM python:3.14-slim

# Install system dependencies for runtime and health checks (curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  pkg-config \
  curl \
  && rm -rf /var/lib/apt/lists/*

# set up working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy stuff from receiver folder to working folder
COPY . /app

# Document the port the container listens on
EXPOSE 8080

# launch the receiver
CMD ["uvicorn", "receiver:app", "--host", "0.0.0.0", "--port", "8080"]

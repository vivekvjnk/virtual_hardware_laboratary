
# Use a Debian-based image
# FROM python:3.9-slim-buster
FROM python:3.9-slim-bookworm

# Set the working directory
WORKDIR /app

# Update package list and install ngspice
RUN apt-get update && \
    apt-get install -y ngspice && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the FastAPI application runs on (if any, adjust as needed)
# For now, I'll assume it runs on port 8000 based on common FastAPI deployments.
# I will verify this later from the python code.
EXPOSE 53328

# Command to run the application using uvicorn
CMD ["uvicorn", "ngspice_simulator_package.mcp_server:app", "--host", "0.0.0.0", "--port", "53328"]

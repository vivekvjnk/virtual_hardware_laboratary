# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy everything (will be filtered by .dockerignore)
COPY . .

# Install dependencies and the workspace project
RUN uv sync --frozen

# Ensure a separate .env file can be mounted or provided
# but specify default environment variables if necessary
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Expose the default port (if the app starts a server later)
EXPOSE 8000

# Default command to run the application
CMD ["aosm"]

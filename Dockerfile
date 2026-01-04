FROM node:20-slim

WORKDIR /app

# 1. Install system dependencies required to install Bun
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Bun
RUN curl -fsSL https://bun.sh/install | bash

# 3. Add Bun to the system PATH
# Note: Since this runs as root, Bun installs to /root/.bun
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

# Install pnpm (original)
RUN npm install -g pnpm

# Install tscircuit for searchLibrary tool
RUN bun install -g tscircuit

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src ./src

RUN pnpm build

# Create directory for library and circuits volumes
RUN mkdir -p /app/lib /app/circuits

# Environment variables
ENV VHL_TRANSPORT=http
ENV PORT=8080
ENV VAP_PORT=8081
ENV VHL_LIBRARY_DIR=/app/lib

# Expose ports
EXPOSE 8080 8081

# Define volumes for persistent storage
VOLUME ["/app/lib", "/app/circuits"]

COPY start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]
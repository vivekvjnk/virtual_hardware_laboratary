FROM node:20-slim

WORKDIR /app

# 1. Install system dependencies + libraries for Sharp and Bun
# We need libvips-dev for sharp and build-essential for native modules
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    make \
    expect \
    g++ \
    unzip \
    libvips-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

# 3. Setup PNPM Home and Path
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="${PATH}:${PNPM_HOME}"
RUN npm install -g pnpm

# 4. Install tscircuit via BUN (This was the critical fix)
# This prevents the 'sharp' module errors you saw with pnpm
RUN bun install -g tscircuit

# 5. Install local project dependencies
COPY package.json pnpm-lock.yaml ./
# Ensure react is in your package.json dependencies!
RUN pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src ./src
COPY dist/runframe ./runframe
COPY workspace ./workspace

RUN pnpm build

# 6. Directory setup for volumes
RUN mkdir -p /app/lib /app/circuits  

# Environment variables
ENV VHL_TRANSPORT=http \
    PORT=8080 \
    VAP_PORT=8081 \
    VHL_LIBRARY_DIR=/app/lib \
    RUNFRAME_STANDALONE_FILE_PATH=/app/runframe/standalone.min.js\
    TSCI_SKIP_CLI_UPDATE=true

EXPOSE 8080 8081

COPY start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]
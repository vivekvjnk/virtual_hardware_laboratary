# syntax=docker/dockerfile:1.7

# ---------------------------
# Stage 1: Builder
# ---------------------------
FROM python:3.12-slim-bookworm AS builder

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install build-time dependencies
RUN apt-get update && apt-get install -y \
    curl \
    make \
    g++ \
    unzip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Bun and PNPM
RUN curl -fsSL https://bun.sh/install | bash
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"
RUN npm install -g pnpm

# Install tscircuit globally
RUN bun install -g tscircuit

# 1. Python venv and dependencies
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt

# 2. Node.js dependencies and build
COPY package.json pnpm-lock.yaml tsconfig.json ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Copy source and build binary
COPY src ./src
RUN pnpm build && \
    pnpm prune --prod # Remove devDependencies after build

# 3. Handle local packages and other directories
COPY packages ./packages
COPY workspace ./workspace
COPY dist/runframe ./runframe
COPY start.sh ./

# Set up editable installs in the venv
RUN /app/venv/bin/pip install -e /app/packages/oh-sdk && \
    /app/venv/bin/pip install --no-deps -e /app/packages/oh-tools

# ---------------------------
# Stage 2: Runtime
# ---------------------------
FROM python:3.12-slim-bookworm AS runtime

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install runtime dependencies ONLY
RUN apt-get update && apt-get install -y \
    curl \
    tmux \
    procps \
    sudo \
    expect \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Bun (for tscircuit if needed)
COPY --from=builder /root/.bun /root/.bun
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

# Copy the entire /app folder (already pruned and built)
# We copy everything because start.sh and editable installs need several subdirs.
COPY --from=builder /app /app

# Environment variables
ENV PATH="/app/venv/bin:${PATH}" \
    VHL_TRANSPORT=http \
    PORT=8080 \
    VAP_PORT=8081 \
    VHL_LIBRARY_DIR=/app/lib \
    RUNFRAME_STANDALONE_FILE_PATH=/app/runframe/standalone.min.js \
    TSCI_SKIP_CLI_UPDATE=true \
    VHL_PROJECT_ROOT=/app

# Initialize runtime directories
RUN mkdir -p /app/lib /app/circuits 

# Expose required ports
EXPOSE 8080 8081 8082 8083 1080 3020

# Entrypoint setup
RUN chmod +x /app/start.sh
CMD ["./start.sh"]
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
RUN curl -fsSL https://bun.sh/install | BUN_INSTALL=/opt/bun bash
ENV BUN_INSTALL="/opt/bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"
RUN npm install -g pnpm

# 1. Copy the pre-built CLI tarball (prepared by prepare_vhl_build.sh)
COPY dist/tscircuit-cli.tgz /tmp/

# 2. Build VHL_runtime
COPY package.json pnpm-lock.yaml tsconfig.json ./
RUN pnpm install --no-frozen-lockfile && pnpm add /tmp/tscircuit-cli.tgz
COPY src ./src
RUN pnpm build && pnpm prune --prod

# 3. Handle local packages and directories
COPY packages ./packages
COPY workspace ./workspace
COPY start.sh ./
COPY dist/runframe /app/runframe_bundle
COPY requirements.txt ./

# 4. Set up Python venv
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt && \
    /app/venv/bin/pip install -e /app/packages/oh-sdk && \
    /app/venv/bin/pip install --no-deps -e /app/packages/oh-tools

# ---------------------------
# Stage 2: Runtime
# ---------------------------
FROM python:3.12-slim-bookworm AS runtime

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tmux \
    procps \
    sudo \
    unzip \
    expect \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Bun (for tscircuit if needed)
COPY --from=builder /opt/bun /opt/bun
ENV BUN_INSTALL="/opt/bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

# Copy the entire /app folder (already pruned and built)
COPY --from=builder /app /app
# Copy the CLI tarball
COPY --from=builder /tmp/tscircuit-cli.tgz /tmp/

# Force-install 'sharp' for the correct platform and ensure CLI is ready
RUN ln -s /app/node_modules/@tscircuit/cli/cli/entrypoint.js /usr/local/bin/tsci && \
    chmod +x /app/node_modules/@tscircuit/cli/cli/entrypoint.js && \
    chmod +x /usr/local/bin/tsci && \
    cd /app && bun add --platform=linux --arch=x64 sharp@0.32.6

# Environment variables
ENV PATH="/app/venv/bin:/app/node_modules/.bin:${PATH}" \
    VHL_TRANSPORT=http \
    PORT=8080 \
    VAP_PORT=8081 \
    VHL_LIBRARY_DIR=/app/lib \
    RUNFRAME_STANDALONE_FILE_PATH=/app/runframe_bundle/standalone.min.js \
    TSCI_SKIP_CLI_UPDATE=true \
    VHL_PROJECT_ROOT=/app \
    VHL_WORKSPACE_DIR=/workspace \
    HOME=/app

# Create workspace directory and ensure /app and /opt/bun are writable for any user
RUN mkdir -p /workspace /app/.tmp /app/lib /app/circuits /app/.vhl_eval && \
    chmod -R 777 /app /workspace /opt/bun

# Expose required ports
EXPOSE 8080 8081 8082 8083 1080 3020

# Entrypoint setup
RUN chmod +x /app/start.sh
CMD ["./start.sh"]
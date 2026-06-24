# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install all necessary dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    g++ \
    make \
    tmux \
    procps \
    sudo \
    unzip \
    expect \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && corepack enable \
    && rm -rf /var/lib/apt/lists/*

# Setup Python environment
COPY packages ./packages
COPY requirements.txt ./
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt && \ 
    /app/venv/bin/pip install -e /app/packages/oh-sdk && \
    /app/venv/bin/pip install --no-deps -e /app/packages/oh-tools

# Install Bun
RUN curl -fsSL https://bun.sh/install | BUN_INSTALL=/opt/bun bash
ENV BUN_INSTALL="/opt/bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"

# 1. Force pnpm to recognize it's running in a non-interactive CI environment
ENV CI=true
# Copy configuration files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json .npmrc .pnpmfile.cjs ./

# Install all dependencies
RUN pnpm install --no-frozen-lockfile --unsafe-perm
RUN npm rebuild sqlite3 --build-from-source --unsafe-perm

# Copy source and build
COPY src ./src
COPY workspace ./workspace
COPY start.sh ./
RUN pnpm build

# Environment Setup
ENV PATH="/app/venv/bin:/app/node_modules/.bin:${PATH}" \
    VHL_TRANSPORT=http \
    PORT=8080 \
    HOME=/app

# Setup permissions
RUN mkdir -p /workspace /app/.tmp /app/lib /app/circuits /app/.vhl_eval && \
    chmod -R 777 /app /workspace

EXPOSE 8080 8081 8082 8083 1080 3020

RUN chmod +x /app/start.sh
CMD ["./start.sh"]
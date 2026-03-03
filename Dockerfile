# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm

WORKDIR /app

# ---------------------------
# 1. System dependencies
# ---------------------------
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y \
        nodejs \
        make \
        expect \
        g++ \
        unzip \
        libvips-dev \
        tmux \
        git \
        procps \
        sudo \
    && rm -rf /var/lib/apt/lists/*


# ---------------------------
# 2. Bun
# ---------------------------
RUN curl -fsSL https://bun.sh/install | bash
ENV BUN_INSTALL="/root/.bun"
ENV PATH="$BUN_INSTALL/bin:$PATH"


# ---------------------------
# 3. PNPM
# ---------------------------
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="${PATH}:${PNPM_HOME}"
RUN npm install -g pnpm


# ---------------------------
# 4. Global tools
# ---------------------------
RUN bun install -g tscircuit


# ---------------------------
# 5. Python venv + base deps
# ---------------------------
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy only dependency definitions first (for caching)
COPY requirements.txt ./requirements.txt

# Install Python deps with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt


# ---------------------------
# 6. Node dependencies layer
# ---------------------------
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile


# ---------------------------
# 7. Copy source (invalidates only app layer)
# ---------------------------
COPY tsconfig.json ./
COPY packages ./packages
COPY src ./src
COPY dist/runframe ./runframe
COPY workspace ./workspace


# ---------------------------
# 8. Editable Python packages
# (fast, runs only when packages change)
# ---------------------------
RUN pip install -e /app/packages/oh-sdk && \
    pip install --no-deps -e /app/packages/oh-tools


# ---------------------------
# 9. Build frontend/runtime
# ---------------------------
RUN pnpm build


# ---------------------------
# 10. Runtime directories
# ---------------------------
RUN mkdir -p /app/lib /app/circuits  


# ---------------------------
# 11. Environment variables
# ---------------------------
ENV VHL_TRANSPORT=http \
    PORT=8080 \
    VAP_PORT=8081 \
    VHL_LIBRARY_DIR=/app/lib \
    RUNFRAME_STANDALONE_FILE_PATH=/app/runframe/standalone.min.js \
    TSCI_SKIP_CLI_UPDATE=true \
    VHL_PROJECT_ROOT=/app


# ---------------------------
# 12. Ports
# ---------------------------
EXPOSE 8080 8081 8082 8083


# ---------------------------
# 13. Entrypoint
# ---------------------------
COPY start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]
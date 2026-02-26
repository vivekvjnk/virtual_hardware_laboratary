FROM python:3.12-slim-bookworm

WORKDIR /app

# 1. Install system dependencies + Node.js + libraries for Sharp and Bun
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
COPY packages ./packages
COPY src ./src
COPY dist/runframe ./runframe
COPY workspace ./workspace

# 6. Install Python dependencies for MCP servers
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install fastmcp pydantic agent-client-protocol deprecation filelock httpx litellm python-frontmatter python-json-logger tenacity websockets lmnr && \
    pip install bashlex binaryornot cachetools libtmux browser-use func-timeout tom-swe && \
    pip install -e /app/packages/oh-sdk && \
    pip install --no-deps -e /app/packages/oh-tools

RUN pnpm build

# 7. Directory setup for volumes
RUN mkdir -p /app/lib /app/circuits  

# Environment variables
ENV VHL_TRANSPORT=http \
    PORT=8080 \
    VAP_PORT=8081 \
    VHL_LIBRARY_DIR=/app/lib \
    RUNFRAME_STANDALONE_FILE_PATH=/app/runframe/standalone.min.js\
    TSCI_SKIP_CLI_UPDATE=true \
    VHL_PROJECT_ROOT=/app

EXPOSE 8080 8081 8082

COPY start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]
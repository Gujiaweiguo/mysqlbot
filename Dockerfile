# Build sqlbot
FROM ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1 AS vector-model
FROM --platform=${BUILDPLATFORM} sqlbot-base:ubuntu24 AS sqlbot-ui-builder
ARG SQLBOT_EMBEDDING_RUNTIME=remote
ENV SQLBOT_HOME=/opt/sqlbot
ENV APP_HOME=${SQLBOT_HOME}/app
ENV UI_HOME=${SQLBOT_HOME}/frontend
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p ${APP_HOME} ${UI_HOME}

WORKDIR /tmp/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend ./
RUN npm run build && mv dist ${UI_HOME}/dist


FROM sqlbot-base:ubuntu24 AS sqlbot-builder
ARG SQLBOT_EMBEDDING_RUNTIME=remote
# Set build environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV APP_HOME=${SQLBOT_HOME}/app
ENV UI_HOME=${SQLBOT_HOME}/frontend
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${APP_HOME}/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV DEBIAN_FRONTEND=noninteractive

# Create necessary directories
RUN mkdir -p ${APP_HOME} ${UI_HOME}

WORKDIR ${APP_HOME}

COPY  --from=sqlbot-ui-builder ${UI_HOME} ${UI_HOME}
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    sh -c 'if test -f "./uv.lock"; then if [ "$SQLBOT_EMBEDDING_RUNTIME" = "local" ]; then uv sync --frozen --no-install-project --extra cpu; else uv sync --frozen --no-install-project; fi; else echo "uv.lock file not found, skipping intermediate-layers"; fi'

COPY ./backend ${APP_HOME}

# Final sync to ensure all dependencies are installed
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$SQLBOT_EMBEDDING_RUNTIME" = "local" ]; then uv sync --frozen --extra cpu; else uv sync --frozen; fi

# Build g2-ssr
FROM sqlbot-base:ubuntu24 AS ssr-builder

WORKDIR /app

COPY g2-ssr/package.json g2-ssr/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY g2-ssr/app.js /app/
COPY g2-ssr/charts /app/charts

# Runtime stage
FROM sqlbot-base:ubuntu24

# Set timezone
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"

# Copy necessary files from builder
COPY start.sh /opt/sqlbot/app/start.sh
COPY g2-ssr/*.ttf /usr/share/fonts/truetype/
COPY --from=sqlbot-builder ${SQLBOT_HOME} ${SQLBOT_HOME}
COPY --from=ssr-builder /app /opt/sqlbot/g2-ssr
COPY --from=vector-model /opt/maxkb/app/model /opt/sqlbot/models

WORKDIR ${SQLBOT_HOME}/app

RUN mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr

EXPOSE 3000 8000 8001

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'curl -f http://localhost:8000/health && curl -f "http://localhost:${MCP_PORT:-8001}/health"' || exit 1

ENTRYPOINT ["sh", "start.sh"]

FROM astral/uv:python3.10-bookworm-slim
WORKDIR /app
# Install skivvy CLI tool into the image
RUN uv tool install skivvy
# Default entrypoint runs the CLI
ENTRYPOINT ["uv", "tool", "run", "skivvy"]
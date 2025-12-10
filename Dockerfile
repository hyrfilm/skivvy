FROM astral/uv:python3.13-bookworm-slim
WORKDIR /app
RUN uv tool install skivvy
COPY ./examples/ ./examples/
CMD ["skivvy", "--version"]

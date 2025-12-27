FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Create directories for agents and venvs
RUN mkdir -p /workspace/agents /workspace/venvs /workspace/logs

# Install base Python packages
RUN pip install --no-cache-dir \
    websockets==12.0 \
    asyncio

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Keep container running
CMD ["/entrypoint.sh"]

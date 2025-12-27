#!/bin/bash
set -e

echo "Starting agents-sandbox container..."
echo "Agents directory: /workspace/agents"
echo "Virtual envs directory: /workspace/venvs"
echo "Logs directory: /workspace/logs"

# Keep container running
tail -f /dev/null

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add environment variables placeholder
ENV PYTHONUNBUFFERED=1
ENV OPENAI_API_KEY=""

# Health check - verify imports work
RUN python -c "from models import DataJanitorAction, DataJanitorObservation, EnvResponse; from env import DataJanitorEnv; from tasks import grade_easy_task, grade_medium_task, grade_hard_task; print('✅ All modules imported successfully')"

# Default command: run mock agent (no API key required)
CMD ["python", "-m", "asyncio", "mock_agent.py"]

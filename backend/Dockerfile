# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first for caching
COPY requirements.txt .

# Upgrade pip and install dependencies
ARG INSTALL_ML_LIBS=false
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && if [ "$INSTALL_ML_LIBS" = "true" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        # Install all requirements except heavy ML packages (torch/transformers/sentence-transformers)
        sed -E '/^(torch|transformers|sentence-transformers)/I d' requirements.txt > /tmp/reqs.txt && \
        pip install --no-cache-dir -r /tmp/reqs.txt; \
    fi

# Copy application code (after installing deps to maximize layer cache)
COPY . /app

# Ensure environment variables are available inside the container
# If you are building from backend directory, this will copy backend/.env → /app/.env
# Do NOT copy secret .env by default; Render will provide env vars via its dashboard
# If you need a local .env for development, it's excluded in .dockerignore

# Expose FastAPI port (use 5000 to match frontend proxy and app config)
EXPOSE 5000

# Start the application on port 5000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]

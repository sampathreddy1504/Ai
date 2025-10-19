# ===============================
#  Base Image
# ===============================
FROM python:3.11-slim AS base

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Working directory
WORKDIR /app

# ===============================
#  Install System Dependencies
# ===============================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===============================
#  Copy requirements and install deps
# ===============================
COPY requirements.txt ./

# Use build arg to control heavy ML installs
ARG INSTALL_ML_LIBS=false

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel \
    && if [ "$INSTALL_ML_LIBS" = "true" ]; then \
        echo "⚙️ Installing full requirements (with ML libs)..." && \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "⚙️ Installing lightweight requirements (no ML libs)..." && \
        grep -viE '^(torch|transformers|sentence-transformers)' requirements.txt > /tmp/reqs.txt && \
        pip install --no-cache-dir -r /tmp/reqs.txt; \
    fi

# ===============================
#  Copy Application Code
# ===============================
COPY . .

# ===============================
#  Runtime Configuration
# ===============================
# You can override these via Render/Env vars
ENV PORT=5000
EXPOSE 5000

# Optional: force UTF-8 locale
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# ===============================
#  Command to Start FastAPI App
# ===============================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]

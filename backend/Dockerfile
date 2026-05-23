# Use the official Playwright Python image — includes Chromium and all system deps.
# This means Playwright browser automation works out of the box.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python dependencies before copying source code so Docker caches this
# layer and only re-builds it when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source
COPY . .

# Create a dedicated directory for the SQLite database so it can be mounted as
# a named volume and survives container restarts / rebuilds.
RUN mkdir -p /app/db

EXPOSE 8000

# Run Alembic migrations first (idempotent — safe to run on every start),
# then launch the production-grade uvicorn server.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]

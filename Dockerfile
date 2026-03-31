# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.13-slim AS build

WORKDIR /app

# Install dependencies into an isolated prefix so we can copy them cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from build stage
COPY --from=build /install /usr/local

# Copy application source
COPY . .

# Create the instance directory (SQLite database lives here)
RUN mkdir -p /app/instance

# Initialise the database schema on first run via an entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "main:app"]


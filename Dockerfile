# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
# Installs Python dependencies into a virtual environment so only the venv
# is copied to the runtime stage (keeps the final image small).
FROM python:3.11-slim AS builder

WORKDIR /app

# Install pip-tools so requirements.txt (pip-compile output) installs cleanly
RUN pip install --no-cache-dir pip-tools

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend source
COPY backend/ .

# Collect static files (whitenoise serves them)
RUN SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

EXPOSE 8000

# Run gunicorn — 4 workers, bind to 0.0.0.0:$PORT
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 4 --access-logfile - --error-logfile -"]

# ==========================================
# Stage 1: Builder Stage
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /app

# Install dependencies into wheels / install directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Final Runtime Stage
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source code and templates
COPY app.py .
COPY templates/ ./templates/

# Expose Flask application port
EXPOSE 5000

# Set environment defaults
ENV FLASK_APP=app.py
ENV PORT=5000

# Start Flask application
CMD ["python", "app.py"]

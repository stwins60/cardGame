# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir --prefix=/install

# Stage 2: Runtime with non-root user
FROM python:3.12-slim

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /install /usr/local


COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5000

CMD ["flask", "--app", "app", "run", "--port", "5000", "--host", "0.0.0.0"]
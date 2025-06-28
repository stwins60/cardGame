# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir --prefix=/install

# Stage 2: Runtime with non-root user
FROM python:3.12-slim

# RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Create a non-root user and group. The user will get their home directory at /home/appuser (-m flag)
# and the group will be created with a specific GID (-g flag).
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

COPY --from=builder /install /usr/local


COPY . .

# Change ownership of the application directory to the non-root user and group (appuser:appgroup)
RUN mkdir -p /app/instance \
    && chown -R 1001:1001 /app \
    && chmod -R 755 /app \
    && chmod -R 700 /app/instance

USER 1001
# USER appuser

EXPOSE 5000

CMD ["flask", "--app", "app", "run", "--port", "5000", "--host", "0.0.0.0"]

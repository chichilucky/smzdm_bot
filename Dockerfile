# Build stage
FROM python:3.12-alpine AS builder

RUN apk update && apk add --no-cache tzdata ca-certificates

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src ./src

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Runtime stage
FROM python:3.12-alpine

WORKDIR /smzdm_bot

ENV TZ=Asia/Shanghai

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/smzdm* /usr/local/bin/
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Copy source for config lookup
COPY src/smzdm_bot/config /smzdm_bot/config

CMD ["smzdm-scheduler"]



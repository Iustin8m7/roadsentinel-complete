# Web gateway image (build context: repository root). Builds the police UI and serves it
# with a reverse proxy to the secure API from one origin.
FROM node:22.12.0-alpine3.21 AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Same-origin deployment: empty API origin, real API (no mocks).
ENV VITE_API_URL="" VITE_USE_MOCKS=""
RUN npm run build

FROM caddy:2.10.2-alpine
COPY deploy/railway-web/Caddyfile /etc/caddy/Caddyfile
COPY --from=ui /ui/dist /srv/app
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
ENV RS_API_UPSTREAM=secure-api.railway.internal:8000
# Unprivileged: Caddy only needs writable scratch dirs (admin API is off, TLS is Railway's).
ENV XDG_DATA_HOME=/tmp/caddy-data XDG_CONFIG_HOME=/tmp/caddy-config
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]

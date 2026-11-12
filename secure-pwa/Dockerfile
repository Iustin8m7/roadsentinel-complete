# syntax=docker/dockerfile:1.7
FROM node:25.2.1-alpine3.21 AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# Static files served by an unprivileged nginx (runs as uid 101, listens on 8080).
FROM nginxinc/nginx-unprivileged:1.27.3-alpine3.20
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
USER 101
EXPOSE 8080

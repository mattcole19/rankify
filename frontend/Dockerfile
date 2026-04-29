# syntax=docker/dockerfile:1.8

FROM node:lts-alpine AS base

ENV NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM base AS dev

COPY . ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM base AS build

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . ./
RUN npm run build

FROM caddy:2-alpine

WORKDIR /app

COPY Caddyfile ./
RUN caddy fmt Caddyfile --overwrite

COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["caddy", "run", "--config", "Caddyfile", "--adapter", "caddyfile"]

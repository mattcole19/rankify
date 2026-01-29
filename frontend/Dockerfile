# syntax=docker/dockerfile:1.8

FROM node:22-slim

ENV NODE_ENV=development \
    HOST=0.0.0.0 \
    PORT=5173

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# ─── Build Stage ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first so this layer is cached when only source changes.
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─── Production Stage ────────────────────────────────────────────────────────
# Serve the compiled static files through nginx.  nginx also proxies /api
# requests to the backend service (see nginx.conf).
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

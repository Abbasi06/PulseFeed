# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

ARG VITE_ADMIN_API_URL
ARG VITE_ADMIN_API_KEY
ENV VITE_ADMIN_API_URL=$VITE_ADMIN_API_URL
ENV VITE_ADMIN_API_KEY=$VITE_ADMIN_API_KEY

RUN npm run build

# Runtime stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3001

CMD ["nginx", "-g", "daemon off;"]

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

# Build-time arguments for Next.js public env vars
ARG NEXT_PUBLIC_BACKEND_URL=http://backend:18800
ARG NEXT_PUBLIC_BACKEND_DIRECT_URL=http://localhost:18800
ARG NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:18800/ws

# Set as environment variables for Next.js build
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_DIRECT_URL=$NEXT_PUBLIC_BACKEND_DIRECT_URL
ENV NEXT_PUBLIC_WEBSOCKET_URL=$NEXT_PUBLIC_WEBSOCKET_URL

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production && \
    npm ci --only=development

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS production
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json

# Install only production dependencies
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Switch to non-root user
USER nextjs

EXPOSE 3000
CMD ["npm", "start"]

# Stage 1: Install dependencies
FROM oven/bun:1.3.4-slim AS deps

WORKDIR /app

COPY package.json bun.lock ./

RUN bun install --frozen-lockfile

# Stage 2: Build the application
FROM oven/bun:1.3.4-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG API_URL=http://api:8000

ENV API_URL=$API_URL

RUN bun run build

# Stage 3: Production runtime
FROM oven/bun:1.3.4-slim

WORKDIR /app

ENV NODE_ENV=production
ENV API_URL=http://api:8000

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["bun", "server.js"]

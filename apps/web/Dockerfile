FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./
# Empty = browser same-origin (rewrites). Internal URL is baked into Next rewrites at build.
ARG NEXT_PUBLIC_API_BASE=
ARG API_INTERNAL_BASE=http://127.0.0.1:8471
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV API_INTERNAL_BASE=$API_INTERNAL_BASE
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3847
ENV HOSTNAME=0.0.0.0
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3847
CMD ["node", "server.js"]

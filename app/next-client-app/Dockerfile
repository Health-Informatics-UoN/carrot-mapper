# 1. Builder (amd64 only)
FROM --platform=linux/amd64 node:20-alpine AS builder
WORKDIR /app

# Install deps
COPY package.json package-lock.json* ./
RUN npm ci

# Copy sources & build Next.js
COPY . .

# Version is resolved from git tags by CI (semantic-release) and passed in here,
# since npm has no built-in equivalent of computing a version from VCS at build
# time. This patches package.json in the built image only - the committed file
# keeps its placeholder value for local dev. /api/health reads this at runtime.
# CI passes an empty string on non-release builds (no tag was cut) - guard against
# that rather than handing npm an empty version, which would fail the build.
ARG APP_VERSION=0.0.0-dev
RUN if [ -n "$APP_VERSION" ]; then \
      npm version --no-git-tag-version --allow-same-version "$APP_VERSION"; \
    fi

RUN npm run build

# 2. Runner (multi-arch)
FROM node:20-alpine AS runner
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

# Copy only what's needed for runtime
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.js ./next.config.js
COPY --from=builder /app/constants ./constants

USER nextjs

CMD ["npm", "start"]

FROM node:22-alpine

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/visualization-schema/package.json packages/visualization-schema/package.json
RUN corepack enable && pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/visualization-schema packages/visualization-schema
WORKDIR /app/apps/web
RUN pnpm build

EXPOSE 3000
CMD ["pnpm", "start"]

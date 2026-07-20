FROM node:22-bookworm-slim AS build

WORKDIR /build
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
ARG NEXT_PUBLIC_AWARE_API_URL
ENV NEXT_PUBLIC_AWARE_API_URL=${NEXT_PUBLIC_AWARE_API_URL}
RUN npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production PORT=8080 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build /build/.next/standalone ./
COPY --from=build /build/.next/static ./.next/static
COPY --from=build /build/public ./public
EXPOSE 8080
CMD ["node", "server.js"]


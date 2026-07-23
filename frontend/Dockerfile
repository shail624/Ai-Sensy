# Frontend production image (Doc 08 §6 — pinned, non-root, minimal).
# Multi-stage: build the Vite bundle with Node, then serve the static output from nginx.
# The runtime carries no Node and no source — only the compiled assets.

# ---- Builder ----
FROM node:20-alpine AS builder
WORKDIR /build

# Dependencies first, so a source-only change reuses the install layer. `npm ci` installs exactly
# what `package-lock.json` pins, including devDependencies — `tsc` and `vite` are both dev deps and
# both run in the build below.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# `npm run build` runs `tsc --noEmit && vite build`: a type error fails the image, never ships.
# VITE_* values are compiled in at build time, so the API base URL is a build argument, not a
# runtime env var. Default is empty = same-origin, which is what the reverse proxy provides.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- Runtime ----
FROM nginx:1.27-alpine AS runtime

# Serve-only config: SPA history fallback plus long-lived caching for fingerprinted assets.
# Proxying, compression and security headers belong to the edge proxy, not here.
#
# The path is relative to this build context (`./frontend`), so the file lives beside this
# Dockerfile. A config kept outside the context is simply not visible to the builder.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

# nginx:alpine ships an unprivileged `nginx` user; the stock image runs the master as root to
# bind :80. Serving on 8080 lets the whole container run as non-root (Doc 08 §26).
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx \
    && touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid
USER nginx

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/bin/sh", "-c", "wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1"]
CMD ["nginx", "-g", "daemon off;"]

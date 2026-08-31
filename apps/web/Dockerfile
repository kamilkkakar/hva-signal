FROM node:22-alpine AS build

WORKDIR /web
# Explicit shipping Vite flags. Unset public-context would also default ON
# in publicContextGate.ts; bake them so hosted cannot silently lose chrome.
ARG VITE_HVA_PUBLIC_CONTEXT=1
ARG VITE_HVA_PLACE_SEARCH=0
ARG VITE_HVA_PLACE_SEARCH_API=0
ARG VITE_HVA_LIVE_DEMO_CONFIRMATION=0
ENV VITE_HVA_PUBLIC_CONTEXT=1
ENV VITE_HVA_PLACE_SEARCH=0
ENV VITE_HVA_PLACE_SEARCH_API=0
ENV VITE_HVA_LIVE_DEMO_CONFIRMATION=0
# Hardcoded (not ARG): Render dashboard VITE_HVA_JUDGE_SHELL=0 must not win.
ENV VITE_HVA_JUDGE_SHELL=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_HVA_JUDGE_SHELL=1
RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache wget gettext

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]

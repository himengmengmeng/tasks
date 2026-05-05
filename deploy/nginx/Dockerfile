FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

EXPOSE 80 443

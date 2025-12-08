# Etapa 1: Build
FROM node:20-alpine as build
WORKDIR /app
COPY package.json package-lock.json ./

# CAMBIO AQUÍ: Agregamos --legacy-peer-deps para ignorar el conflicto de versiones
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build -- --configuration production

# Etapa 2: Serve
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/erp-frontend/browser /usr/share/nginx/html
EXPOSE 80
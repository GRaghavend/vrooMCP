# Multi-stage build: compile the Vite app, then serve the static output
# with nginx. The API calls (api.ts) are made by the user's browser, not
# by this container -- so this image needs no network path to the backend
# container at all; it only needs the backend's port published to the
# host (see ../docker-compose.yml), same as running `vite preview` would.
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

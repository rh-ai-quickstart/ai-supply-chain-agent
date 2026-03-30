FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . ./

ARG VITE_API_BASE_URL=http://backend:5001
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM docker.io/nginxinc/nginx-unprivileged:stable-alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

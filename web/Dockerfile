FROM node:19.6.0-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

FROM nginx:1.23.3-alpine
COPY km-web.conf /etc/nginx/conf.d/km-web.conf
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /var/www/km-web

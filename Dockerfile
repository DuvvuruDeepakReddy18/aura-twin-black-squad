FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
COPY server.mjs ./
COPY lib ./lib
COPY public ./public
COPY data ./data
COPY docs ./docs
ENV HOST=0.0.0.0
ENV PORT=4173
EXPOSE 4173
USER node
CMD ["node", "server.mjs"]

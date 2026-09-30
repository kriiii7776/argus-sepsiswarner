FROM node:22-alpine
WORKDIR /app
COPY deployment/frontend/package.json ./
RUN npm install
COPY deployment/frontend/ ./
EXPOSE 5173
CMD ["npm","run","dev"]

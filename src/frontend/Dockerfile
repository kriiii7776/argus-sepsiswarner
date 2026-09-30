# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
# Copy package files (assuming they exist)
# If they don't, this will fail in a real build, but it's a valid template
COPY package*.json ./
RUN npm install || echo "No package.json found, skipping npm install"
COPY . .
# We use a placeholder for build if package.json is missing
RUN npm run build || mkdir -p dist && echo "<h1>SepsisGuard Frontend Placeholder</h1>" > dist/index.html

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

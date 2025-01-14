# Base Node image
FROM node:18-alpine as base
WORKDIR /app
ENV NODE_ENV=production

# Frontend build stage
FROM base as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Backend build stage
FROM base as backend-build
WORKDIR /app/backend
COPY backend/package*.json ./
RUN npm install
COPY backend/ .

# Production stage
FROM base
WORKDIR /app

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copy backend
COPY --from=backend-build /app/backend /app/backend

# Set environment variables
ENV PORT=5001
ENV OPENAI_API_KEY=""

# Expose ports
EXPOSE 5001
EXPOSE 5173

# Start the application
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
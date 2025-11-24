# instadock/frontend/Dockerfile

# Stage 1: Install dependencies and build the application
FROM node:20-alpine AS builder
WORKDIR /app/frontend

# Copy dependencies and install
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy source code and run the Next.js build
COPY frontend/ .
RUN npm run build

# Stage 2: Production runtime image
FROM node:20-alpine AS runner
WORKDIR /app/frontend

# Copy only essential files for serving
COPY --from=builder /app/frontend/public ./public
COPY --from=builder /app/frontend/.next ./.next
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY frontend/package.json frontend/next.config.mjs .

EXPOSE 3000

# Start the built application
CMD ["npm", "start"]
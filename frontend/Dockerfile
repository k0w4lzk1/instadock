# instadock/frontend/Dockerfile

# Stage 1: Install dependencies and build the application
FROM node:20-alpine AS builder
WORKDIR /app/frontend

# Copy dependencies and install
# FIX: Removed 'frontend/' prefix because the build context is already ./frontend
COPY package.json package-lock.json ./ 
RUN npm install

# Copy source code and run the Next.js build
# FIX: Removed 'frontend/' prefix
COPY . .
RUN npm run build

# Stage 2: Production runtime image
FROM node:20-alpine AS runner
WORKDIR /app/frontend

# Copy only essential files for serving
# NOTE: The paths here are correct because they reference the builder stage's internal path (/app/frontend/)
COPY --from=builder /app/frontend/public ./public
COPY --from=builder /app/frontend/.next ./.next
COPY --from=builder /app/frontend/node_modules ./node_modules
# FIX: Removed 'frontend/' prefix from package.json and next.config.mjs copy
COPY package.json next.config.mjs ./

EXPOSE 3000

# Start the built application
CMD ["npm", "start"]
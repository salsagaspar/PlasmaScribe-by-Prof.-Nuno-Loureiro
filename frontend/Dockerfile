FROM node:20-slim

WORKDIR /app

# Copy package configurations
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

# Vite requires '--host' to be accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]

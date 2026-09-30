FROM node:22-slim
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
# Session + memory live in volumes so re-deploys don't force a new QR scan.
VOLUME ["/app/auth", "/app/data"]
CMD ["node", "src/index.js"]

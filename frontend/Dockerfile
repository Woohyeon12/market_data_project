FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ENV PORT=3000

RUN npm run build

CMD ["npm", "run", "start"]

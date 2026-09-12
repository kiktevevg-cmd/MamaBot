FROM node:20-bookworm AS web-build
WORKDIR /app/webapp
COPY webapp/package*.json ./
RUN npm ci
COPY webapp/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/mama_bot.db

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=web-build /app/webapp/dist /app/webapp/dist
RUN chmod +x /app/start.sh

EXPOSE 3000
CMD ["/app/start.sh"]
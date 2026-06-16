FROM python:3.12-alpine
RUN apk add --no-cache bash curl docker-cli docker-cli-compose
WORKDIR /app
COPY server.py .
EXPOSE 9000
CMD ["python", "server.py"]

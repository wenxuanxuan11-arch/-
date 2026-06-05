FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV HOST=0.0.0.0
ENV PORT=8080

WORKDIR /app

COPY server.py index.html styles.css app.js ./
COPY assets ./assets

RUN mkdir -p /data

VOLUME ["/data"]
EXPOSE 8080

ENTRYPOINT []
CMD ["python", "server.py"]

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev gcc pkg-config supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-all.txt ./
RUN pip install --no-cache-dir --no-deps -r requirements-all.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles /app/static \
    && python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000 8001

CMD ["supervisord", "-c", "/app/supervisord.conf"]

FROM python:3.11-slim

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt daphne

COPY . .

CMD ["daphne", "-b", "0.0.0.0", "-p", "8001", "room_service.asgi:application"]
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handlers.py .

CMD ["kopf", "run", "--standalone", "--all-namespaces", "/app/handlers.py"]

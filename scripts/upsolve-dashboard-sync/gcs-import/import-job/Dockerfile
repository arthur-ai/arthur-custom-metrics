FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY import_from_gcs.py .

CMD ["python3", "import_from_gcs.py"]

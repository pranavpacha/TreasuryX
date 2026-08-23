FROM python:3.12-slim

WORKDIR /app

# tesseract-ocr enables real OCR text extraction in the CV pipeline. Without it, the
# pipeline still runs every other stage and reports a clear "OCR unavailable" warning
# instead of failing -- remove this line to slim the image if OCR isn't needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# $PORT is set by most PaaS hosts (e.g. Render); falls back to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

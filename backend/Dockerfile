FROM python:3.12-slim

WORKDIR /app

# Note: the Tesseract OCR binary is NOT installed here to keep the image lean.
# To enable OCR inside the container, uncomment the following two lines:
# RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
#     && rm -rf /var/lib/apt/lists/*
# Without it, the CV pipeline still runs every other stage and reports a clear
# "OCR unavailable" warning instead of failing.

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

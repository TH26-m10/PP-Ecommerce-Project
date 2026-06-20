FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lrt_proxy.py .

EXPOSE 9000

CMD ["uvicorn", "lrt_proxy:app", "--host", "0.0.0.0", "--port", "9000"]

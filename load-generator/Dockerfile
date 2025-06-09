FROM python:3.11-slim
WORKDIR /app
COPY main.py .
RUN pip install flask prometheus_client psycopg2-binary faker
CMD ["python", "main.py"]

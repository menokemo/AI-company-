FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir setuptools wheel
COPY *.py .
CMD ["python", "crew.py"]

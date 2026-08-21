FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN opentelemetry-bootstrap -a install

CMD ["opentelemetry-instrument", "streamlit", "run", "start_server.py"]

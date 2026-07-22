FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["streamlit", "run", "start_server.py"]
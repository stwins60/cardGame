FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 5000

# CMD ["python", "app.py"]
CMD ["flask", "--app", "app", "run", "--port", "5000", "--host", "0.0.0.0"]
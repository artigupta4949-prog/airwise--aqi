FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
RUN useradd -r appuser
USER appuser
ENV PORT=8080
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 "app:create_app()"

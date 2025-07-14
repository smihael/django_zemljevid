# Use official Python image with system dependencies for PostGIS
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
     apt-get install -y binutils libproj-dev gdal-bin && \
     rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt 

# Copy Django project and app
COPY spomenicarji /app/spomenicarji
COPY zemljevid /app/zemljevid
COPY manage.py /app/manage.py

# Collect static files
RUN python -m manage collectstatic --noinput

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (default Django)
EXPOSE 8000

# Use gunicorn for production deployment
CMD ["gunicorn", "spomenicarji.wsgi:application", "--bind", "0.0.0.0:8000"]

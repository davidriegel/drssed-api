FROM python:3.12

WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App Code kopieren
COPY . .

# Logs & Static Ordner erstellen
RUN mkdir -p logs app/static/{clothing_images,profile_pictures,temp,outfit_collages}

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:api"]
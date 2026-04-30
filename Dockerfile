FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs app/static/{clothing_images,profile_pictures,temp,outfit_collages}

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:api"]
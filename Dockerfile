FROM python:3

LABEL maintainer="Maksym Kotiash"

COPY run.py requirements.txt app/

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "run.py"]

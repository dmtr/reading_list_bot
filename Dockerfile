FROM python:3.8.1-alpine
RUN apk add build-base libffi-dev openssl-dev postgresql-dev
RUN pip install -U pip && pip install cryptography
RUN mkdir -p /app/bot
COPY requirements.txt /app/requirements.txt
WORKDIR /app/

RUN pip install -r requirements.txt
COPY . /app/

CMD ["python", "main.py"]

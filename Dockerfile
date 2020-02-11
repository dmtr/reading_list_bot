FROM python:3.8.1-alpine
RUN pip install -U pip
RUN mkdir -p /app/bot
COPY requirements.txt /app/requirements.txt
WORKDIR /app/

RUN pip install -r requirements.txt
COPY . /app/

CMD ["python", "main.py"]

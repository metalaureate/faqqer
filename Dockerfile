FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT ["python"]
CMD ["faqqer_bot.py"]
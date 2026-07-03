FROM python:latest
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
ENV API_KEY=abcd1234efgh5678
EXPOSE 5000
CMD ["python", "server.py"]

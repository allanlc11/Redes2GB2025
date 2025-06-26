FROM python:3.9-alpine
WORKDIR /app
COPY node.py .
RUN pip install redis
CMD ["python", "node.py"]
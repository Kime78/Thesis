FROM python:3
WORKDIR /app/filereceiver 
COPY . .
RUN pip install -r requirements.txt
CMD ["fastapi", "run"]
from typing import Union
from fastapi import FastAPI, UploadFile, HTTPException
from kafka import KafkaProducer
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka Producer Configuration
producer = KafkaProducer(
    bootstrap_servers=['kafka:29092'],  
    value_serializer=lambda x: x  
)

topic_name = 'file-chunks'

app = FastAPI()

@app.post("/upload")
async def upload_file(uploaded_file: UploadFile):
    chunk_size = 1 * 1024 * 1024 // 2 # 500 kib
    nr_of_chunks = 0

    try:
        while True:
            chunk = await uploaded_file.read(chunk_size)
            if not chunk:
                break  # Exit loop if no more data

            # Send chunk to Kafka
            future = producer.send(topic_name, value=chunk)
            nr_of_chunks += 1

            # Wait for the send to complete (optional)
            try:
                future.get(timeout=10)  # Wait up to 10 seconds
            except Exception as e:  # Catch general exceptions
                logger.error(f"Failed to send chunk {nr_of_chunks}: {e}")
                raise HTTPException(status_code=500, detail=f"Kafka error: {e}")

            logger.info(f"Sent chunk {nr_of_chunks}")

        # Flush remaining messages
        producer.flush()
        logger.info("All chunks sent successfully")

        return {
            "filename": uploaded_file.filename,
            "chunks_sent": nr_of_chunks,
            "message": "File uploaded and processed successfully"
        }

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
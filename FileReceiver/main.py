from typing import Union

from fastapi import FastAPI, UploadFile

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/upload")
async def upload_file(uploaded_file: UploadFile):
    chunk_size = 4 * 1024 * 1024 #MiB 
    nr_of_chunks = 0
    while True:
        chunk = await uploaded_file.read(chunk_size)
        nr_of_chunks += 1
        if not chunk:
            break
        print(nr_of_chunks) 
# FROM python:3.9-slim
# WORKDIR /app
# COPY . .
# RUN pip install -r requirements.txt
# # RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chunk.proto
# COPY ./main.py .
# CMD ["python", "main.py"]

# Stage 1: Builder
FROM python:3 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Final image
FROM python:3-slim
WORKDIR /app/storagenode

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

CMD ["python", "main.py"]

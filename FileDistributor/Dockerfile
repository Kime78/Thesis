# FROM python:3
# WORKDIR /app/filedistribuitor
# COPY . .
# RUN pip install -r requirements.txt

# CMD ["python", "main2.py"]

# Stage 1: Builder
FROM python:3 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Final image
FROM python:3-slim
WORKDIR /app/filedistribuitor

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

CMD ["python", "main2.py"]

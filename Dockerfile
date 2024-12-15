FROM python:3.12-alpine

# Install system dependencies including Node.js
RUN apk add --no-cache \
    nodejs \
    npm \
    git \
    build-base \
    postgresql-dev

# Install Python dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY ./app ./app

# Copy Prisma schema
COPY ./prisma ./prisma

# Generate Prisma client
RUN python -m prisma generate

# Run the application
CMD ["python", "-m", "app"]
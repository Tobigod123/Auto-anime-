# Use the official Python image as the base image
FROM python:3.8-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV TZ=UTC

# Create and set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the entire project into the container
COPY . .

# Run the bot
CMD ["python", "bot.py"]

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code into the container
COPY bot.py .

# Set environment variable for token (optional)
# ENV TELEGRAM_BOT_TOKEN="YOUR_TOKEN_HERE"

# Run the bot
CMD ["python", "bot.py"]

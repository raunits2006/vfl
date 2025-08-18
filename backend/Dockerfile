# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by psycopg2 or other packages
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Adding --no-cache-dir to ensure fresh download, and --upgrade pip first
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Add the scripts directory to PATH (pip installed executables often go here)
# For python:3.10-slim, /usr/local/bin should already be in PATH, but being explicit can help.
ENV PATH="/usr/local/bin:${PATH}"

# Copy the rest of the application code
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

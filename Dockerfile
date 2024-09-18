# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /b2pserve

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy the rest of the application code into the container
COPY b2pserve.py .

# Create a 'completed' directory inside the container
RUN mkdir /b2pserve/completed

# Set permissions for the 'completed' directory
RUN chmod 755 /b2pserve/completed

# Open port 8000
EXPOSE 8000

# Set the entry point for the container
CMD ["python", "b2pserve.py"]
# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Install C++ build tools
RUN apt-get update && apt-get install -y build-essential

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Run app.py when the container launches
CMD ["python3", "main.py"]

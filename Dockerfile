# Dockerfile for OpsAgent Streamlit app
FROM python:3.11-slim

# set workdir
WORKDIR /app

# copy project files
COPY . /app

# install system deps (for matplotlib)
RUN apt-get update && apt-get install -y build-essential libcairo2-dev libglib2.0-0 libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*

# install python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# expose Streamlit port
EXPOSE 8501

ENV PYTHONUNBUFFERED=1

# default command: run Streamlit UI
CMD ["streamlit", "run", "app/ui_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]

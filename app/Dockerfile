FROM python:3.9-slim-bookworm
LABEL maintainer="lakehouse"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        curl \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/app

COPY requirements.txt /home/app/requirements.txt
RUN pip install --no-cache-dir -r /home/app/requirements.txt

COPY . /home/app

EXPOSE 8051

CMD ["streamlit", "run", "core/1_🏠_Home.py", "--server.port=8051", "--server.address=0.0.0.0"]

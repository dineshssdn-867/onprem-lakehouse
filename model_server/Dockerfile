FROM python:3.9-slim-bookworm

LABEL maintainer "admin@lakehouse.io"

RUN apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install openjdk-17-jdk -yqq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin


RUN pip install mlflow==2.3.2 && \
    pip install awscli --upgrade --user && \
    pip install boto3==1.16.46 && \
    pip install flask && \
    pip install pyspark==3.3.2

# Add Hadoop AWS jars for S3/MinIO access
RUN PYSPARK_JARS=$(python3 -c "import pyspark, os; print(os.path.join(os.path.dirname(pyspark.__file__), 'jars'))") && \
    python3 -c "import urllib.request; urllib.request.urlretrieve('https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar', '${PYSPARK_JARS}/aws-java-sdk-bundle-1.12.367.jar')" && \
    python3 -c "import urllib.request; urllib.request.urlretrieve('https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar', '${PYSPARK_JARS}/hadoop-aws-3.3.4.jar')"

ENV PORT 5000

RUN mkdir -p /opt/mlflow

COPY files/run.sh /
COPY main.py /opt/mlflow/main.py

ENTRYPOINT ["/run.sh"]

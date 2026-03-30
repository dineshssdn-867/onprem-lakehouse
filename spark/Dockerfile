FROM apache/spark:3.5.8

USER root

# Install prerequisites
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN curl -O https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.28.3/bundle-2.28.3.jar \
    && curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar \
    && curl -O https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.1/iceberg-spark-runtime-3.5_2.12-1.10.1.jar \
    && curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    && mv bundle-2.28.3.jar /opt/spark/jars \
    && mv aws-java-sdk-bundle-1.12.367.jar /opt/spark/jars \
    && mv iceberg-spark-runtime-3.5_2.12-1.10.1.jar /opt/spark/jars \
    && mv hadoop-aws-3.3.4.jar /opt/spark/jars

ENV PATH="/opt/spark/bin:${PATH}"

# Fix spark user home directory (base image sets it to /nonexistent)
RUN mkdir -p /home/spark && chown spark:spark /home/spark && \
    usermod -d /home/spark spark
ENV HOME=/home/spark

USER spark

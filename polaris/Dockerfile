FROM alpine:3.19

RUN apk add --no-cache curl bash

# Install MinIO client
RUN curl -fSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

COPY bootstrap.sh /bootstrap/bootstrap.sh
RUN chmod +x /bootstrap/bootstrap.sh

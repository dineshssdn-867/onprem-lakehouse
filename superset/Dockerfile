FROM apache/superset:3.1.3

USER root

# Install Trino SQLAlchemy driver and Redis for Celery
RUN pip install --no-cache-dir trino redis gevent

# Copy configuration and entrypoint scripts
COPY superset_config.py /app/superset_config.py
COPY superset-init.sh /app/superset-init.sh
COPY superset-worker.sh /app/superset-worker.sh
RUN chmod +x /app/superset-init.sh /app/superset-worker.sh

USER superset

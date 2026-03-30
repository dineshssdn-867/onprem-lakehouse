#!/bin/bash
set -e

echo ">>> Superset: Running database migrations..."
superset db upgrade

echo ">>> Superset: Creating admin user (if not exists)..."
superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@lakehouse.local \
  --password admin123 || true

echo ">>> Superset: Initializing roles and permissions..."
superset init

echo ">>> Superset: Registering Trino datasource..."
python3 -c "
from superset.app import create_app
app = create_app()

with app.app_context():
    from superset.models.core import Database
    from superset.extensions import db as sadb

    existing = sadb.session.query(Database).filter_by(database_name='Lakehouse (Trino)').first()
    if not existing:
        trino_db = Database(
            database_name='Lakehouse (Trino)',
            sqlalchemy_uri='trino://trino@trino:8080/lakehouse',
            expose_in_sqllab=True,
            allow_run_async=True,
            allow_ctas=False,
            allow_cvas=False,
        )
        sadb.session.add(trino_db)
        sadb.session.commit()
        print('Trino database connection created.')
    else:
        print('Trino database connection already exists.')
"

echo ">>> Superset: Starting gunicorn server..."
exec gunicorn \
  --bind 0.0.0.0:8088 \
  --workers 2 \
  --worker-class gevent \
  --timeout 120 \
  --limit-request-line 0 \
  --limit-request-field_size 0 \
  "superset.app:create_app()"

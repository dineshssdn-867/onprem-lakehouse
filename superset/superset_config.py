import os
from cachelib.redis import RedisCache

# ------------------------------------------------------------------
# Metadata database (Superset's own tables)
# ------------------------------------------------------------------
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://"
    f"{os.environ.get('SUPERSET_DB_USER', 'admin')}:"
    f"{os.environ.get('SUPERSET_DB_PASS', 'admin123')}@"
    f"{os.environ.get('SUPERSET_DB_HOST', 'postgresql')}:"
    f"{os.environ.get('SUPERSET_DB_PORT', '5432')}/"
    f"{os.environ.get('SUPERSET_DB_NAME', 'supersetdb')}"
)

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "lakehouse-superset-secret-key")

# ------------------------------------------------------------------
# Celery (async queries via Redis)
# ------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")


class CeleryConfig:
    broker_url = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/0"
    result_backend = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/1"
    task_annotations = {"*": {"rate_limit": "10/s"}}
    worker_prefetch_multiplier = 1
    task_acks_late = True


CELERY_CONFIG = CeleryConfig

# ------------------------------------------------------------------
# SQL Lab results backend (required for async queries)
# ------------------------------------------------------------------
RESULTS_BACKEND = RedisCache(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    db=2,
    key_prefix="superset_results_",
)

# ------------------------------------------------------------------
# General
# ------------------------------------------------------------------
SUPERSET_WEBSERVER_PORT = 8088
SUPERSET_LOAD_EXAMPLES = False

# Disable HTTPS/CSRF for local Docker development
TALISMAN_ENABLED = False
WTF_CSRF_ENABLED = False

# ------------------------------------------------------------------
# Feature flags
# ------------------------------------------------------------------
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Thumbnail generation base URL
WEBDRIVER_BASEURL = "http://superset:8088/"

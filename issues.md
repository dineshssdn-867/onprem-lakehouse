# Lakehouse Project - Issue Tracker

> Generated: 2026-03-21 | Status: Pre-migration audit
> Verified against running containers and current codebase

---

## CRITICAL - Must Fix Before Pipeline Runs

### C-01: Iceberg JAR Scala version vs Spark base image
- **Files:** `spark/Dockerfile:10`, `scripts/sparksession.py:38-39`
- **Status:** VERIFIED OK - Spark 3.5.8 ships with `scala-library-2.12.18.jar`, so `iceberg-spark-runtime-3.5_2.12-1.10.1.jar` is correct
- **Action:** None needed

### C-02: Column name mismatch — `user_id`/`business_id` vs `userid`/`businessid`
- **Files:**
  - `scripts/als_model.py:46-48` uses `user_id`, `business_id`
  - `scripts/train_model.py:78-79` uses `userid`, `businessid`
  - `model_server/main.py:54,61` uses `userid`, `businessid`
  - `app/script/make.py:25-26` queries `WHERE businessid = ...`
- **Issue:** `als_model.py` trains with different column names than `train_model.py`. Whichever script runs, the model will expect those specific column names. Downstream consumers (model_server, make.py) assume `userid`/`businessid`.
- **Impact:** Model prediction will fail if trained with wrong script
- **Fix:** Align all scripts to use `userid`/`businessid` (matches bronze transform output)

### C-03: SQL injection in authenticator.py
- **File:** `app/core/auth/authenticator.py:13,24`
- **Issue:** f-string interpolation of user input directly into SQL
  ```python
  cursor.execute(f"SELECT DISTINCT(account_name) FROM bronze.user_account WHERE account_name = '{account_name}'")
  ```
- **Fix:** Use parameterized queries: `cursor.execute("SELECT ... WHERE account_name = ?", (account_name,))`

### C-04: SQL injection in make.py
- **File:** `app/script/make.py:25-26`
- **Issue:** Same f-string SQL injection pattern with `businessid` values from API response
- **Fix:** Use parameterized queries

### C-05: Auth logic bug — password check is `password == user`
- **File:** `app/core/auth/authenticator.py:66`
- **Issue:** Password is compared to the username, not to the `account_pass` column from the database
  ```python
  if submit and user == username and password == user:
  ```
- **Fix:** Fetch and compare against `account_pass` from `bronze.user_account`

### C-06: Auth logic operator precedence bug
- **File:** `app/core/auth/authenticator.py:76`
- **Issue:** Missing parentheses causes wrong evaluation
  ```python
  elif submit and user != username or password != user:
  # Evaluates as: (submit and user != username) or (password != user)
  ```
- **Fix:** `elif submit and (user != username or password != user):`

### C-07: Streamlit app imports PySpark (not in requirements.txt, not needed)
- **Files:**
  - `app/core/pages/1_💡_Recommender.py:2-6,16-20` — imports SparkSession, ALSModel
  - `app/script/utils.py:6-7,12-15,24` — imports SparkSession, reads JSON via Spark
- **Issue:** PySpark is not in `app/requirements.txt`. The app will crash on import. The Flask model server already handles ALS predictions via API — no need for PySpark in the Streamlit app.
- **Fix:** Remove PySpark usage; use pandas for JSON reading in utils.py; remove ALSModel loading from Recommender.py

### C-08: `const.st` is None — Recommender.py crashes
- **File:** `app/core/pages/1_💡_Recommender.py:23-24`
- **Issue:** `st = const.st` but `constants.py` sets `st = None`. Then `components = st.components.v1` raises `AttributeError`.
- **Fix:** Import streamlit directly: `import streamlit as st`

### C-09: Function signature mismatch — `initialize_res_widget`
- **File:** `app/core/pages/1_💡_Recommender.py:73`
- **Issue:** Called with 1 arg `initialize_res_widget(streamlit)` but function expects 2 args `(cfg, st)`
- **Fix:** Should be `initialize_res_widget(line2, streamlit)`

### C-10: dbt profiles.yml hardcoded `localhost`
- **File:** `restaurant_analytis/profiles.yml:6`
- **Issue:** `host: localhost` — dbt cannot reach Trino inside Docker network
- **Fix:** Change to `host: trino`

### C-11: dim_date.sql uses Spark SQL syntax, incompatible with Trino
- **File:** `restaurant_analytis/models/silver/transform/dim_date.sql:8-40`
- **Issue:** Functions like `format_datetime()`, `day_of_week()`, `day_of_month()`, `last_day_of_month()`, `week_of_year()` are Spark SQL — Trino equivalents differ
- **Fix:** Rewrite using Trino date functions (`date_format()`, `day_of_week()`, `day()`, `last_day_of_month()`, etc.)

---

## HIGH - Should Fix

### H-01: PySpark version mismatch between Spark and model_server
- **Files:** `spark/Dockerfile:1` (Spark 3.5.8), `model_server/Dockerfile:19` (PySpark 3.3.2)
- **Issue:** Model trained on Spark 3.5.8, served by PySpark 3.3.2 — potential API/format incompatibility
- **Fix:** Align `model_server/Dockerfile` to `pyspark==3.5.8`

### H-02: Model server missing Iceberg JARs
- **File:** `model_server/Dockerfile:22-24`
- **Issue:** Only downloads AWS SDK + hadoop-aws JARs, no Iceberg runtime. If model server needs to read Iceberg tables, it will fail.
- **Fix:** Add `iceberg-spark-runtime` JAR download to model_server Dockerfile

### H-03: Dual AWS SDK JARs in Spark container
- **File:** `spark/Dockerfile:8-9`
- **Issue:** Downloads both `aws-java-sdk-bundle-1.12.367.jar` (SDK v1) and `bundle-2.28.3.jar` (SDK v2). Both loaded on classpath — potential conflicts.
- **Fix:** Evaluate if both are needed. SDK v1 bundle is typically required by hadoop-aws; SDK v2 may be unnecessary.

### H-04: `sparksession.py` env var name mismatch
- **File:** `scripts/sparksession.py:3-4`
- **Issue:** Uses `os.environ['AWS_ACCESS_KEY']` / `os.environ['AWS_SECRET_KEY']` but Makefile passes `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- **Fix:** Use `os.environ.get('AWS_ACCESS_KEY', os.environ.get('AWS_ACCESS_KEY_ID', 'minio'))`

### H-05: `mlflow.env` hardcoded localhost
- **File:** `mlflow.env:5`
- **Issue:** `MLFLOW_S3_ENDPOINT_URL=http://localhost:9000` — won't work inside Docker
- **Fix:** Change to `http://minio:9000`

### H-06: Legacy dependencies in requirements.txt (project root)
- **File:** `requirements.txt`
- **Issue:** Still contains `PyMySQL==1.0.2`, `PyHive==0.6.5`, `dbt-spark==1.4.0`, `dbt-spark[PyHive]`, `dbt-spark[session]`
- **Fix:** Remove PyMySQL, PyHive, dbt-spark; keep only `dbt-trino==1.4.0`

### H-07: Polaris bootstrap `restart: "no"` — no retry on failure
- **File:** `docker-compose.yml:76`
- **Issue:** If bootstrap fails (network race, Polaris not ready), the catalog is never created and everything downstream fails silently
- **Fix:** Change to `restart: on-failure` with retry limit, or add better healthcheck waits

### H-08: No healthchecks in docker-compose.yml
- **File:** `docker-compose.yml`
- **Issue:** No `healthcheck` blocks for PostgreSQL, Polaris, Trino, MinIO, MLflow. Services may start before dependencies are ready.
- **Fix:** Add healthchecks; use `depends_on` with `condition: service_healthy`

### H-09: Directory name typo `restaurant_analytis`
- **Files:** `restaurant_analytis/` directory, `dbt_project.yml:5,10,35`, `profiles.yml:1`, `Makefile` (multiple), `env.sh`
- **Issue:** Missing 'c' — should be `restaurant_analytics`
- **Fix:** Rename directory and update all references

### H-10: Model server port passed as string
- **File:** `model_server/main.py:89`
- **Issue:** `app.run(debug=True, host='0.0.0.0', port='5001')` — port should be int
- **Fix:** `port=5001`

---

## MEDIUM - Good to Fix

### M-01: Hardcoded credentials throughout codebase
- **Files:** `.env`, `docker-compose.yml:43-48,51-53`, `spark/spark-defaults.conf:13`, `model_server/main.py:13-16`, `polaris/bootstrap.sh:12-16`, `trino/catalog/lakehouse.properties:7`
- **Issue:** MinIO (`minio`/`minio123`), PostgreSQL (`admin`/`admin123`), Polaris (`polaris`/`polaris_secret_123`) credentials hardcoded in multiple files
- **Mitigation:** Acceptable for local dev; add `.env.example` template, ensure `.env` is in `.gitignore`

### M-02: Hardcoded model server auth token
- **File:** `model_server/main.py:31`
- **Issue:** `if data["token"] != "systemapi":` — weak security
- **Fix:** Use env var for token validation

### M-03: `generate_data.py` default endpoint is localhost
- **File:** `scripts/generate_data.py:295`
- **Issue:** `os.environ.get("AWS_S3_ENDPOINT", "http://localhost:9000")` — fallback won't work in Docker
- **Fix:** Change default to `http://minio:9000`

### M-04: Duplicate imports in transform scripts
- **Files:** `scripts/bronze_user_account.py:1-4`, `scripts/bronze_business_transform.py:1-2`
- **Issue:** `Window` imported twice (from `pyspark.sql` and `pyspark.sql.window`)
- **Fix:** Remove duplicate import

### M-05: Duplicate import in widgets.py
- **File:** `app/UI/widgets.py:1,5-6`
- **Issue:** `import constants as const` appears twice with unnecessary `sys.path.append('../')`
- **Fix:** Remove duplicate import and sys.path hack

### M-06: Bare except clauses
- **Files:** `app/script/utils.py:32`, `app/UI/widgets.py:66`, `app/detail.py:32`
- **Issue:** `except:` catches all exceptions including KeyboardInterrupt
- **Fix:** Use `except Exception:` at minimum

### M-07: Hardcoded fallback image URL in utils.py
- **File:** `app/script/utils.py:33`
- **Issue:** External URL `https://toohotel.com/...` used as fallback poster image
- **Fix:** Use a local placeholder image

### M-08: Variable name typo in train_model.py
- **File:** `scripts/train_model.py:140`
- **Issue:** `ortherDate` — should be `orderedDate` or `sortedDate`
- **Fix:** Rename variable

### M-09: ETL DAG is a stub
- **File:** `airflow/dags/etl.py`
- **Issue:** Contains dummy operators, not a real ETL pipeline
- **Note:** Acceptable since Airflow is being replaced by Kestra in Phase 2

### M-10: `detail.py` is unused/deprecated
- **File:** `app/detail.py`
- **Issue:** Hardcoded restaurant name on line 53, duplicate of functionality in Recommender.py
- **Fix:** Remove file if confirmed unused

---

## LOW - Nice to Have

### L-01: `version` attribute in docker-compose.yml is obsolete
- **File:** `docker-compose.yml`
- **Issue:** Docker Compose warns about obsolete `version` attribute on every command
- **Fix:** Remove the `version:` line

### L-02: Trino image not version-pinned
- **File:** `docker-compose.yml:79`
- **Issue:** `image: trinodb/trino:latest` — not reproducible
- **Fix:** Pin to specific version (e.g., `trinodb/trino:440`)

### L-03: Polaris image not version-pinned
- **File:** `docker-compose.yml:37`
- **Issue:** `image: apache/polaris:latest`
- **Fix:** Pin to specific version

### L-04: MLflow boto3 version very old
- **File:** `mlflow/Dockerfile:7`
- **Issue:** `pip install boto3==1.16.46` — from Dec 2020
- **Fix:** Update to recent compatible version

### L-05: Missing bronze layer dbt models
- **File:** `restaurant_analytis/models/`
- **Issue:** No `bronze/` subdirectory with view models. Sources are defined in `sources.yml` but no models reference them.
- **Note:** Bronze tables are created by Spark scripts; dbt only transforms Silver/Gold. May be by design.

---

## Issue Count Summary

| Priority | Count | Description |
|----------|-------|-------------|
| CRITICAL | 11 | Blocks pipeline or causes runtime crashes |
| HIGH | 10 | Causes failures in specific scenarios |
| MEDIUM | 10 | Code quality, security hardening |
| LOW | 5 | Best practices, reproducibility |
| **Total** | **36** | |

---

## Fix Order Recommendation

1. **Phase A — Unblock Streamlit app:** C-07, C-08, C-09, C-05, C-06, C-03, C-04
2. **Phase B — Unblock dbt-trino:** C-10, C-11, H-06, H-09
3. **Phase C — Fix model pipeline:** C-02, H-01, H-02, H-04
4. **Phase D — Infrastructure hardening:** H-07, H-08, H-03, H-05
5. **Phase E — Cleanup:** All MEDIUM and LOW items

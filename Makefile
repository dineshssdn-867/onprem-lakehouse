# ============================================================================
# Lakehouse Pipeline Makefile
# ============================================================================
# Usage:
#   make pipeline          # Run the full pipeline end-to-end
#   make generate-data     # Generate synthetic data + upload to MinIO
#   make etl               # Run bronze ingestion + transforms + feature store
#   make dbt               # Run dbt transforms (Silver + Gold)
#   make train             # Train ALS model + register in MLflow
#   make clean             # Remove generated data and dbt artifacts
# ============================================================================

SHELL := /bin/bash

# -- Docker containers --------------------------------------------------------
SPARK_CONTAINER   := spark-master
TRINO_CONTAINER   := trino

# -- Paths --------------------------------------------------------------------
SCRIPTS_DIR       := scripts
OUTPUT_DIR        := $(SCRIPTS_DIR)/output
DBT_DIR           := restaurant_analytis
SPARK_WORKDIR     := /opt/spark/work-dir/scripts

# -- Spark submit command inside container ------------------------------------
DOCKER_EXEC       := docker exec
SPARK_EXEC        := $(DOCKER_EXEC) $(SPARK_CONTAINER)
SPARK_SUBMIT      := $(SPARK_EXEC) /opt/spark/bin/spark-submit --master spark://spark-master:7077
SPARK_ENV         := -e AWS_ACCESS_KEY=minio -e AWS_SECRET_KEY=minio123 -e AWS_S3_ENDPOINT=http://minio:9000 -e AWS_REGION=us-east-1 -e AWS_ACCESS_KEY_ID=minio -e AWS_SECRET_ACCESS_KEY=minio123 -e MLFLOW_S3_ENDPOINT_URL=http://minio:9000

# ============================================================================
# Full pipeline
# ============================================================================
.PHONY: pipeline
pipeline: generate-data setup-spark etl dbt train
	@echo ""
	@echo "======================================"
	@echo "  Pipeline completed successfully!"
	@echo "======================================"

# ============================================================================
# Step 1: Generate synthetic data + upload to MinIO
# ============================================================================
.PHONY: generate-data
generate-data:
	@echo "\n>>> Generating synthetic Yelp dataset..."
	cd $(SCRIPTS_DIR) && python3 generate_data.py --upload
	@echo ">>> Data generated and uploaded to MinIO."

# ============================================================================
# Step 2: Prepare Spark container (copy scripts + install deps)
# ============================================================================
# Helper: pipe file into container (workaround for docker cp failing on WSL2 bind mounts)
define copy_to_spark
	cat $(SCRIPTS_DIR)/$(1) | docker exec -i $(SPARK_CONTAINER) tee $(SPARK_WORKDIR)/$(1) > /dev/null
endef

SCRIPT_FILES := sparksession.py create_schema.py \
	bronze_restaurant.py bronze_user.py bronze_review.py \
	bronze_checkin.py bronze_tip.py \
	bronze_business_transform.py bronze_user_account.py \
	feature_store.py train_model.py model_register.py

.PHONY: setup-spark
setup-spark:
	@echo "\n>>> Setting up Spark container..."
	$(SPARK_EXEC) mkdir -p $(SPARK_WORKDIR)
	@$(foreach f,$(SCRIPT_FILES),echo "  -> $(f)" && $(call copy_to_spark,$(f)) &&) true
	@echo ">>> Installing Python dependencies in Spark container..."
	$(DOCKER_EXEC) -u 0 $(SPARK_CONTAINER) pip3 install mlflow==2.3.2 boto3 --quiet
	@echo ">>> Spark container ready."

# ============================================================================
# Step 3: ETL pipeline (Bronze ingestion + transforms + feature store)
# ============================================================================
.PHONY: etl
etl: create-schemas bronze-ingest bronze-transform feature-store
	@echo ">>> ETL pipeline complete."

.PHONY: create-schemas
create-schemas:
	@echo "\n>>> Creating namespaces (bronze, feature_store)..."
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/create_schema.py

.PHONY: bronze-ingest
bronze-ingest:
	@echo "\n>>> Ingesting bronze layer..."
	@echo "  -> bronze.restaurant"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_restaurant.py
	@echo "  -> bronze.user"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_user.py
	@echo "  -> bronze.review"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_review.py
	@echo "  -> bronze.checkin"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_checkin.py
	@echo "  -> bronze.tip"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_tip.py
	@echo ">>> Bronze ingestion complete."

.PHONY: bronze-transform
bronze-transform:
	@echo "\n>>> Running bronze transforms..."
	@echo "  -> bronze.restaurant_transform"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_business_transform.py
	@echo "  -> bronze.user_account"
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/bronze_user_account.py
	@echo ">>> Bronze transforms complete."

.PHONY: feature-store
feature-store:
	@echo "\n>>> Creating feature store..."
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		$(SPARK_WORKDIR)/feature_store.py
	@echo ">>> Feature store ready."

# ============================================================================
# Step 4: dbt transforms (Bronze -> Silver -> Gold)
# ============================================================================
.PHONY: dbt
dbt: dbt-deps dbt-run
	@echo ">>> dbt transforms complete."

.PHONY: dbt-deps
dbt-deps:
	@echo "\n>>> Installing dbt dependencies..."
	cd $(DBT_DIR) && dbt deps --profiles-dir .

.PHONY: dbt-run
dbt-run:
	@echo "\n>>> Running dbt models (Silver + Gold)..."
	cd $(DBT_DIR) && dbt run --profiles-dir .
	@echo ">>> dbt run complete."

.PHONY: dbt-test
dbt-test:
	@echo "\n>>> Running dbt tests..."
	cd $(DBT_DIR) && dbt test --profiles-dir .

# ============================================================================
# Step 5: Train ALS model + register in MLflow
# ============================================================================
.PHONY: train
train: train-model register-model
	@echo ">>> Model training and registration complete."

.PHONY: train-model
train-model:
	@echo "\n>>> Training ALS model..."
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		/opt/spark/bin/spark-submit --master spark://spark-master:7077 \
		--packages org.mlflow:mlflow-spark:2.3.2 \
		$(SPARK_WORKDIR)/train_model.py
	@echo ">>> Model training complete. Check MLflow at http://localhost:5000"

.PHONY: register-model
register-model:
	@echo "\n>>> Registering model in MLflow..."
	$(DOCKER_EXEC) $(SPARK_ENV) $(SPARK_CONTAINER) \
		python3 $(SPARK_WORKDIR)/model_register.py
	@echo ">>> Model registered as 'restaurant_recommender' (Production)."

# ============================================================================
# Utilities
# ============================================================================
.PHONY: verify-trino
verify-trino:
	@echo "\n>>> Verifying Trino can see Iceberg tables..."
	$(DOCKER_EXEC) $(TRINO_CONTAINER) trino --execute \
		"SHOW SCHEMAS FROM lakehouse"
	$(DOCKER_EXEC) $(TRINO_CONTAINER) trino --execute \
		"SHOW TABLES FROM lakehouse.bronze"

.PHONY: verify-data
verify-data:
	@echo "\n>>> Checking row counts..."
	$(DOCKER_EXEC) $(TRINO_CONTAINER) trino --execute \
		"SELECT 'restaurant' as tbl, count(*) as cnt FROM lakehouse.bronze.restaurant UNION ALL SELECT 'user', count(*) FROM lakehouse.bronze.\"user\" UNION ALL SELECT 'review', count(*) FROM lakehouse.bronze.review UNION ALL SELECT 'checkin', count(*) FROM lakehouse.bronze.checkin UNION ALL SELECT 'tip', count(*) FROM lakehouse.bronze.tip"

.PHONY: verify-silver
verify-silver:
	@echo "\n>>> Checking silver layer..."
	$(DOCKER_EXEC) $(TRINO_CONTAINER) trino --execute \
		"SHOW TABLES FROM lakehouse.dev_silver"

.PHONY: verify-gold
verify-gold:
	@echo "\n>>> Checking gold layer..."
	$(DOCKER_EXEC) $(TRINO_CONTAINER) trino --execute \
		"SELECT count(*) as total_reviews FROM lakehouse.dev_gold.analyses_review"

.PHONY: clean
clean:
	@echo "\n>>> Cleaning generated data..."
	rm -rf $(OUTPUT_DIR)
	rm -rf $(DBT_DIR)/target
	rm -rf $(DBT_DIR)/dbt_packages
	@echo ">>> Clean complete."

.PHONY: status
status:
	@echo "\n>>> Service status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | sort

.PHONY: help
help:
	@echo ""
	@echo "Lakehouse Pipeline"
	@echo "===================="
	@echo ""
	@echo "Full pipeline:"
	@echo "  make pipeline        Run everything end-to-end"
	@echo ""
	@echo "Individual steps:"
	@echo "  make generate-data   Generate synthetic data + upload to MinIO"
	@echo "  make setup-spark     Copy scripts + install deps in Spark container"
	@echo "  make etl             Bronze ingestion + transforms + feature store"
	@echo "  make dbt             Run dbt-trino transforms (Silver + Gold)"
	@echo "  make train           Train ALS model + register in MLflow"
	@echo ""
	@echo "Verification:"
	@echo "  make verify-trino    Check Trino sees Iceberg tables"
	@echo "  make verify-data     Check row counts in bronze layer"
	@echo "  make verify-silver   Check silver layer tables"
	@echo "  make verify-gold     Check gold layer row count"
	@echo ""
	@echo "Utilities:"
	@echo "  make status          Show Docker service status"
	@echo "  make dbt-test        Run dbt tests"
	@echo "  make clean           Remove generated data + dbt artifacts"
	@echo ""

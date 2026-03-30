# Migration Plan: Hive Metastore → Unity Catalog & Metabase → Apache Superset

## Executive Summary

**Feasibility**: ✅ **YES - Both migrations are highly feasible and recommended**

This migration will modernize your lakehouse with:
- **Unity Catalog**: Open-source, universal governance with better security, ABAC, MLflow integration, and multi-format support (Delta, Iceberg, Parquet)
- **Apache Superset**: More powerful BI tool with better visualizations, SQL Lab, semantic layer, and active community
- **Database Strategy**: Keep MySQL for all backends (UC, Superset, Airflow, existing Hive metadata)

---

## Phase 1: Unity Catalog Migration (Priority: High)

### Architecture Changes
```
BEFORE: Spark → Hive Metastore → MySQL (metastore_db)
AFTER:  Spark → Unity Catalog Server → MySQL (unity_catalog_db)
```

### Implementation Steps

#### 1. Prepare MySQL for Unity Catalog
- Create new database: `unity_catalog_db` in existing MySQL container
- Configure Unity Catalog to use MySQL backend (instead of default PostgreSQL)
- Update Unity Catalog hibernate.properties for MySQL

#### 2. Add Unity Catalog Services (docker-compose.yml)
- Deploy UC server container (port 8080)
- Deploy UC UI container (port 3001)
- Configure MySQL connection (same MySQL container, different database)
- Mount UC configuration files

#### 3. Update Spark Configuration
- Upgrade Spark to 3.5.3+ (currently 3.3)
- Upgrade Delta Lake to 3.2.1+ (currently 2.2.0)
- Add unitycatalog-spark JAR dependencies
- Configure spark-defaults.conf with UC catalog settings
- Update hive-site.xml for UC integration

#### 4. Migrate Metadata from Hive to Unity Catalog
- Create UC catalogs/schemas structure (main catalog → bronze/silver/gold schemas)
- Use SYNC TABLE command for all external Delta tables
- Preserve MinIO data locations (no data movement)
- Migrate schemas: bronze, dev_silver, dev_gold
- Verify all tables accessible through UC

#### 5. Update All Integrations
- **Airflow DAGs**: Update catalog references from `hive_metastore.bronze` to `main.bronze`
- **dbt profiles.yml**: Configure for Unity Catalog (via Thrift Server)
- **Spark Thrift Server**: Point to Unity Catalog instead of Hive
- **MLflow**: Update table references to UC format

### Benefits
- Fine-grained access control (row/column level security)
- Attribute-based access control (ABAC) with tags
- Seamless MLflow integration for model governance
- Multi-format support (Delta, Iceberg via UniForm, Parquet, etc.)
- Centralized governance across data & AI assets
- Better audit logging and lineage tracking
- Future-proof for Iceberg migration

---

## Phase 2: Apache Superset Migration (Priority: Medium)

### Architecture Changes
```
BEFORE: Metabase → PostgreSQL → Spark Thrift Server
AFTER:  Apache Superset → MySQL (superset_db) → Spark Thrift Server
```

### Implementation Steps

#### 1. Prepare MySQL for Superset
- Create new database: `superset_db` in existing MySQL container
- Configure Superset to use MySQL backend (instead of PostgreSQL)
- Update Superset config with MySQL connection string

#### 2. Deploy Apache Superset
- Add Superset service to docker-compose.yml
- Configure MySQL as metadata database
- Change Superset port to 3000 (or keep 8088 and move Airflow)
- Install necessary database drivers (Spark/Hive driver)
- Configure Redis for caching (optional but recommended)

#### 3. Connect Data Sources
- Configure Spark Thrift Server connection in Superset
- Setup connection to Unity Catalog tables
- Configure SQLAlchemy connection string
- Test connectivity and query execution
- Setup SSL if needed

#### 4. Migrate Dashboards & Content
- Export dashboard list from Metabase (manual documentation)
- Recreate critical charts in Superset (no automated migration)
- Configure Superset semantic layer for reusable metrics
- Setup saved queries in SQL Lab
- Create dashboard collections for different user groups

#### 5. User & Permission Migration
- Export user list from Metabase
- Create users in Superset (can use same auth as Streamlit app)
- Configure role-based access control (RBAC)
- Setup row-level security rules if needed
- Configure dashboard permissions

### Benefits
- **50+ chart types** vs Metabase's limited options
- **SQL Lab**: Advanced SQL IDE for ad-hoc analysis
- **Semantic layer**: Define metrics once, reuse everywhere
- **Better performance**: Query result caching, async queries
- **Python integration**: Custom visualizations with Python
- **Active development**: Apache project with strong community
- **Headless BI**: API-first for programmatic access
- **Advanced filters**: Cross-filtering, cascading filters

---

## Phase 3: Database Consolidation

### Final MySQL Structure
```
MySQL Container (mysql:3306)
├── metastore_db          # Hive Metastore (keep for backup/rollback)
├── unity_catalog_db      # Unity Catalog metadata (NEW)
├── superset_db           # Apache Superset metadata (NEW)
└── (existing databases)

MySQL Container (mysql-airflow:3307)
└── airflow               # Airflow metadata (unchanged)

PostgreSQL Container (postgresql:5432)
└── metabaseappdb         # Metabase (keep during parallel run, remove after)
```

### MySQL Configuration Updates
- Increase max_connections (default 151 → 300)
- Configure connection pooling
- Optimize buffer pool size for metadata queries
- Setup automated backups for all databases

---

## Phase 4: Testing & Validation

### 1. Unity Catalog Validation
- Verify all tables discoverable in UC
- Test CRUD operations (CREATE, READ, UPDATE, DELETE)
- Validate permissions and access control
- Test queries through Spark Thrift Server
- Verify dbt transformations execute correctly
- Check MLflow can read/write UC tables

### 2. Apache Superset Validation
- Compare dashboard accuracy vs Metabase
- Test query performance and caching
- Validate data freshness/real-time updates
- User acceptance testing
- Test embedded dashboards (if applicable)

### 3. End-to-End Pipeline Testing
- Run complete ETL pipeline (Airflow → Spark → UC)
- Execute dbt transformations
- Train ML model using UC tables
- Verify Superset reflects latest data
- Test model serving with UC integration

### 4. Performance Benchmarking
- Compare query latency (Hive vs UC)
- Dashboard load times (Metabase vs Superset)
- Metadata operation speed
- Concurrent user handling

---

## Phase 5: Cutover & Cleanup

### 1. Parallel Operation Period (2-3 weeks)
- Run both Hive Metastore + Unity Catalog
- Run both Metabase + Superset
- Monitor system health and performance
- Gradual user migration to new systems
- Collect feedback and address issues

### 2. Final Cutover
- Switch all Airflow DAGs to UC
- Update all dbt references to UC
- Redirect all users to Superset
- Disable Hive Metastore service
- Disable Metabase service

### 3. Cleanup & Decommissioning
- Backup Hive Metastore MySQL database
- Export Metabase PostgreSQL database
- Remove hive-metastore container from docker-compose.yml
- Remove Metabase and PostgreSQL containers
- Archive old configuration files
- Update documentation

---

## Configuration Changes Required

### 1. docker-compose.yml
- Add unity-catalog-server service
- Add unity-catalog-ui service
- Add superset service
- Add redis service (for Superset caching)
- Remove hive-metastore (after migration)
- Remove metabase (after migration)
- Remove postgresql (after migration)

### 2. Spark Configuration
- spark-defaults.conf: Add UC catalog configurations
- Upgrade Spark JARs and Delta Lake JARs
- Add unitycatalog-spark JAR

### 3. Airflow Configuration
- Update DAG scripts (all bronze_*.py, etl.py, etc.)
- Update SparkSubmitOperator catalog references
- Update connection settings

### 4. dbt Configuration
- profiles.yml: Update catalog configuration
- sources.yml: Change from hive_metastore to UC catalog
- models: Update {{ source() }} references

### 5. Environment Variables
- Add UC_* variables for Unity Catalog
- Add SUPERSET_* variables for Apache Superset
- Update existing MySQL connection settings

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Spark 3.3 → 3.5 breaking changes | High | Test in staging, review changelog |
| Delta Lake 2.2 → 3.2 compatibility | Medium | Verify table format compatibility |
| MySQL connection pool exhaustion | Medium | Increase max_connections to 300+ |
| Dashboard recreation effort | High | Prioritize top 20% critical dashboards |
| User training requirement | Medium | Create video tutorials, documentation |
| Query performance regression | Medium | Benchmark and optimize UC configuration |
| Data loss during migration | Critical | Use SYNC (non-destructive), backup first |
| Unity Catalog learning curve | Medium | Provide UC documentation and examples |

---

## Timeline Estimate

### Week 1-2: Unity Catalog Setup
- Setup UC server with MySQL backend
- Upgrade Spark 3.3 → 3.5, Delta 2.2 → 3.2
- Test UC connectivity and basic operations

### Week 3: Metadata Migration
- Migrate bronze layer schemas and tables
- Migrate silver layer schemas and tables
- Migrate gold layer schemas and tables
- Validate data accessibility

### Week 4: Integration Updates
- Update Airflow DAGs for UC
- Update dbt profiles and models
- Update Spark Thrift Server configuration
- Update MLflow integrations

### Week 5-6: Apache Superset Deployment
- Deploy Superset with MySQL backend
- Configure data source connections
- Setup authentication and RBAC
- Begin dashboard recreation

### Week 7-8: Dashboard Migration
- Recreate critical dashboards (top 20%)
- Recreate remaining dashboards
- User training sessions
- Performance optimization

### Week 9: Testing & Validation
- Comprehensive testing (data, BI, ETL, ML)
- Performance benchmarking
- User acceptance testing
- Bug fixes and adjustments

### Week 10-11: Parallel Operation
- Run both systems side-by-side
- Monitor for issues
- Gradual user cutover
- Collect feedback

### Week 12: Final Cutover
- Switch all traffic to new systems
- Decommission old services
- Cleanup and documentation

**Total Duration**: ~12 weeks (3 months) for complete migration

---

## Rollback Strategy

If issues arise during migration:

1. **Immediate Rollback**: Keep Hive Metastore and Metabase running in parallel
2. **Data Safety**: SYNC TABLE preserves original data in MinIO
3. **Configuration Backup**: Version control all config changes
4. **Database Backup**: Daily MySQL backups of all databases
5. **Phased Approach**: Migrate one layer at a time (bronze → silver → gold)

---

## Success Criteria

- ✅ All Delta Lake tables accessible via Unity Catalog
- ✅ Zero data loss during migration
- ✅ Query performance equal or better than Hive Metastore
- ✅ All Airflow DAGs execute successfully
- ✅ All dbt models compile and run
- ✅ MLflow models can read from UC tables
- ✅ Critical dashboards recreated in Superset
- ✅ User acceptance rating > 80%
- ✅ No production incidents during cutover

---

## Next Steps After Approval

1. Create detailed Unity Catalog docker-compose service definition
2. Create Apache Superset docker-compose service definition
3. Write Unity Catalog MySQL schema initialization scripts
4. Create metadata migration scripts (Hive → UC)
5. Update all Spark configuration files
6. Create Airflow DAG migration templates
7. Update dbt project configuration
8. Create step-by-step migration runbooks
9. Generate user training materials
10. Setup monitoring and alerting for new services

---

## Detailed Technical Specifications

### Unity Catalog Docker Service Configuration

```yaml
unity-catalog-server:
  image: unitycatalog/unitycatalog:latest
  container_name: unity-catalog-server
  ports:
    - "8080:8080"
  environment:
    - UC_DATABASE_TYPE=mysql
    - UC_DATABASE_HOST=mysql
    - UC_DATABASE_PORT=3306
    - UC_DATABASE_NAME=unity_catalog_db
    - UC_DATABASE_USER=admin
    - UC_DATABASE_PASSWORD=admin
    - UC_S3_ENDPOINT=http://minio:9000
    - UC_S3_ACCESS_KEY=minio
    - UC_S3_SECRET_KEY=minio123
  volumes:
    - ./unity-catalog/conf:/etc/unitycatalog
    - ./unity-catalog/data:/var/lib/unitycatalog
  depends_on:
    - mysql
    - minio
  networks:
    - data_network

unity-catalog-ui:
  image: unitycatalog/unitycatalog-ui:latest
  container_name: unity-catalog-ui
  ports:
    - "3001:3000"
  environment:
    - UC_SERVER_URL=http://unity-catalog-server:8080
  depends_on:
    - unity-catalog-server
  networks:
    - data_network
```

### Apache Superset Docker Service Configuration

```yaml
redis:
  image: redis:7-alpine
  container_name: superset-redis
  ports:
    - "6379:6379"
  networks:
    - data_network

superset:
  image: apache/superset:latest
  container_name: superset
  ports:
    - "3000:8088"
  environment:
    - SUPERSET_SECRET_KEY=superset_secret_key_change_me
    - DATABASE_DIALECT=mysql
    - DATABASE_USER=admin
    - DATABASE_PASSWORD=admin
    - DATABASE_HOST=mysql
    - DATABASE_PORT=3306
    - DATABASE_DB=superset_db
    - REDIS_HOST=redis
    - REDIS_PORT=6379
  volumes:
    - ./superset/config:/app/pythonpath
    - ./superset/data:/app/superset_home
  depends_on:
    - mysql
    - redis
  networks:
    - data_network
```

### Updated Spark Configuration (spark-defaults.conf)

```properties
# Existing configurations
spark.jars=jars/*
spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension
spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog
spark.sql.warehouse.dir=s3a://lakehouse/
spark.hadoop.fs.s3a.endpoint=http://minio:9000
spark.hadoop.fs.s3a.access.key=minio
spark.hadoop.fs.s3a.secret.key=minio123
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.connection.ssl.enabled=false
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem

# NEW Unity Catalog configurations
spark.sql.catalog.unity=io.unitycatalog.spark.UCSingleCatalog
spark.sql.catalog.unity.uri=http://unity-catalog-server:8080
spark.sql.catalog.unity.token=
spark.sql.defaultCatalog=unity
```

### Unity Catalog Metadata Migration Script

```sql
-- Connect to Unity Catalog and create catalog structure
CREATE CATALOG IF NOT EXISTS main;
USE CATALOG main;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Sync Bronze Layer Tables
SYNC TABLE main.bronze.user
FROM hive_metastore.bronze.user
SET OWNER admin;

SYNC TABLE main.bronze.restaurant
FROM hive_metastore.bronze.restaurant
SET OWNER admin;

SYNC TABLE main.bronze.review
FROM hive_metastore.bronze.review
SET OWNER admin;

SYNC TABLE main.bronze.tip
FROM hive_metastore.bronze.tip
SET OWNER admin;

SYNC TABLE main.bronze.checkin
FROM hive_metastore.bronze.checkin
SET OWNER admin;

-- Sync Silver Layer Tables
SYNC TABLE main.silver.dim_user
FROM hive_metastore.dev_silver.dim_user
SET OWNER admin;

SYNC TABLE main.silver.dim_restaurant
FROM hive_metastore.dev_silver.dim_restaurant
SET OWNER admin;

SYNC TABLE main.silver.dim_date
FROM hive_metastore.dev_silver.dim_date
SET OWNER admin;

SYNC TABLE main.silver.fact_review
FROM hive_metastore.dev_silver.fact_review
SET OWNER admin;

-- Sync Gold Layer Tables
SYNC TABLE main.gold.analyses_review
FROM hive_metastore.dev_gold.analyses_review
SET OWNER admin;
```

### Updated dbt profiles.yml for Unity Catalog

```yaml
restaurant_analytis:
  target: dev
  outputs:
    dev:
      type: spark
      method: thrift
      host: spark-thrift-server
      port: 10000
      schema: bronze  # default schema
      catalog: main   # Unity Catalog catalog name
      threads: 6
```

### Updated dbt sources.yml for Unity Catalog

```yaml
version: 2

sources:
  - name: bronze
    database: main      # Unity Catalog catalog
    schema: bronze
    tables:
      - name: restaurant
      - name: user
      - name: review
      - name: checkin
      - name: tip

  - name: silver
    database: main      # Unity Catalog catalog
    schema: silver
    tables:
      - name: fact_review
      - name: dim_user
      - name: dim_restaurant
```

### Airflow DAG Updates Example

```python
# BEFORE (Hive Metastore)
ingest_user = SparkSubmitOperator(
    task_id='ingest_user',
    application="../airflow/scripts/bronze_user.py",
    conf={
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog"
    }
)

# AFTER (Unity Catalog)
ingest_user = SparkSubmitOperator(
    task_id='ingest_user',
    application="../airflow/scripts/bronze_user.py",
    conf={
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.sql.catalog.unity": "io.unitycatalog.spark.UCSingleCatalog",
        "spark.sql.catalog.unity.uri": "http://unity-catalog-server:8080",
        "spark.sql.catalog.unity.token": "",
        "spark.sql.defaultCatalog": "unity"
    }
)
```

---

## Resource Requirements

### Hardware/System Resources

| Component | Current | Recommended After Migration |
|-----------|---------|----------------------------|
| Total RAM | 16GB minimum | 24GB minimum |
| CPU Cores | 8 cores | 12 cores |
| Disk Space | 50GB | 100GB |
| Network | 1 Gbps | 1 Gbps |

### Container Resource Allocation

| Service | Memory | CPU |
|---------|--------|-----|
| Unity Catalog Server | 2GB | 1 core |
| Unity Catalog UI | 512MB | 0.5 core |
| Apache Superset | 2GB | 1 core |
| Redis | 512MB | 0.5 core |
| MySQL (increased) | 4GB | 2 cores |

---

## Monitoring & Observability

### Key Metrics to Monitor

1. **Unity Catalog**
   - Metadata query latency
   - Catalog API response times
   - Number of active connections
   - Failed authentication attempts

2. **Apache Superset**
   - Dashboard load times
   - Query execution times
   - Cache hit/miss ratio
   - Active user sessions

3. **MySQL**
   - Connection pool utilization
   - Query execution times
   - Database size growth
   - Replication lag (if applicable)

4. **Overall System**
   - End-to-end pipeline execution time
   - Data freshness (time from ingestion to visualization)
   - Error rates across all services
   - Resource utilization (CPU, memory, disk)

---

## Training & Documentation Requirements

### User Training Materials Needed

1. **For Data Engineers**
   - Unity Catalog concepts and architecture
   - Catalog/schema/table hierarchy
   - Access control and permissions
   - Migration from Hive to UC SQL syntax differences

2. **For Analysts/BI Users**
   - Apache Superset interface overview
   - Creating dashboards and charts
   - SQL Lab usage
   - Differences from Metabase

3. **For Administrators**
   - Unity Catalog administration
   - Superset user and role management
   - Backup and recovery procedures
   - Troubleshooting common issues

### Documentation to Create/Update

1. Architecture diagrams (with UC and Superset)
2. Data catalog documentation
3. API documentation for UC
4. Dashboard creation guidelines
5. Runbooks for common operations
6. Incident response procedures
7. Performance tuning guide

---

## Cost Analysis

### Infrastructure Costs

| Item | Current Cost | After Migration | Difference |
|------|--------------|-----------------|------------|
| Compute (containers) | Baseline | +15% (new services) | ↑ |
| Storage | Baseline | ~Same (metadata only) | → |
| Network | Baseline | ~Same | → |
| Maintenance effort | High (aging stack) | Lower (modern tools) | ↓ |

### Time Investment

| Activity | Estimated Hours |
|----------|----------------|
| Planning & design | 40 hours |
| UC setup & configuration | 60 hours |
| Metadata migration | 40 hours |
| Superset deployment | 40 hours |
| Dashboard recreation | 80 hours |
| Testing & validation | 60 hours |
| Documentation | 40 hours |
| Training | 20 hours |
| **Total** | **380 hours** |

---

## Conclusion

This migration plan provides a comprehensive, phased approach to modernizing your data lakehouse infrastructure. By replacing Hive Metastore with Unity Catalog and Metabase with Apache Superset, you'll gain:

- **Better governance** with fine-grained access controls
- **Improved performance** through modern architectures
- **Future-proofing** with open standards and active communities
- **Enhanced capabilities** for both data engineering and analytics

The 12-week timeline allows for thorough testing and gradual migration, minimizing risk while maximizing benefits. The use of MySQL as a unified database backend simplifies operations and reduces complexity.

**Recommendation**: Proceed with Phase 1 (Unity Catalog) first, validate success, then begin Phase 2 (Superset). This staged approach reduces risk and allows for course correction if needed.

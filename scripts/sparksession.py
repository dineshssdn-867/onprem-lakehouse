import os

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']
AWS_S3_ENDPOINT = os.environ['AWS_S3_ENDPOINT']
AWS_BUCKET_NAME = 'lakehouse'


def spark_session(spark_session):

    spark = spark_session.builder \
        .appName('Lakehouse Iceberg Ingestion') \
        .master('spark://spark-master:7077') \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.polaris.type", "rest") \
        .config("spark.sql.catalog.polaris.uri", "http://polaris:8181/api/catalog") \
        .config("spark.sql.catalog.polaris.credential", "polaris:polaris_secret_123") \
        .config("spark.sql.catalog.polaris.scope", "PRINCIPAL_ROLE:ALL") \
        .config("spark.sql.catalog.polaris.warehouse", "lakehouse") \
        .config("spark.sql.catalog.polaris.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.sql.catalog.polaris.s3.endpoint", AWS_S3_ENDPOINT) \
        .config("spark.sql.catalog.polaris.s3.path-style-access", "true") \
        .config("spark.sql.catalog.polaris.s3.access-key-id", AWS_ACCESS_KEY) \
        .config("spark.sql.catalog.polaris.s3.secret-access-key", AWS_SECRET_KEY) \
        .config("spark.sql.catalog.polaris.s3.region", "us-east-1") \
        .config("spark.executorEnv.AWS_REGION", "us-east-1") \
        .config("spark.sql.defaultCatalog", "polaris") \
        .config("spark.hadoop.fs.s3a.access.key", AWS_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", AWS_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.endpoint", AWS_S3_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config('spark.hadoop.fs.s3a.aws.credentials.provider', 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider') \
        .config('spark.sql.warehouse.dir', f's3a://{AWS_BUCKET_NAME}/') \
        .config('spark.jars.packages', 'org.apache.hadoop:hadoop-aws:3.3.4') \
        .config('spark.driver.extraClassPath', '/opt/spark/jars/hadoop-aws-3.3.4.jar:/opt/spark/jars/bundle-2.28.3.jar:/opt/spark/jars/aws-java-sdk-bundle-1.12.367.jar:/opt/spark/jars/iceberg-spark-runtime-3.5_2.12-1.10.1.jar') \
        .config('spark.executor.extraClassPath', '/opt/spark/jars/hadoop-aws-3.3.4.jar:/opt/spark/jars/bundle-2.28.3.jar:/opt/spark/jars/aws-java-sdk-bundle-1.12.367.jar:/opt/spark/jars/iceberg-spark-runtime-3.5_2.12-1.10.1.jar') \
        .getOrCreate()

    spark.sparkContext.setLogLevel("INFO")

    return spark

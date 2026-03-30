#!/bin/sh
# Bootstrap script to:
#   1. Create MinIO buckets (lakehouse, mlflow, raw-data)
#   2. Create the Polaris catalog pointing to s3://lakehouse/
# Runs in minio/mc image with curl installed.

set -e

POLARIS_HOST="${POLARIS_HOST:-polaris}"
POLARIS_PORT="${POLARIS_PORT:-8181}"
POLARIS_URL="http://${POLARIS_HOST}:${POLARIS_PORT}"
POLARIS_CLIENT_ID="${POLARIS_CLIENT_ID:-polaris}"
POLARIS_CLIENT_SECRET="${POLARIS_CLIENT_SECRET:-polaris_secret_123}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minio}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minio123}"

# ── Step 1: Create MinIO buckets ──────────────────────────────────────
echo "Waiting for MinIO to be ready at ${MINIO_ENDPOINT}..."
until curl -s -o /dev/null -w "%{http_code}" "${MINIO_ENDPOINT}/minio/health/live" | grep -q "200"; do
  echo "  MinIO not ready yet, retrying in 3s..."
  sleep 3
done
echo "MinIO is ready!"

echo "Configuring MinIO client..."
mc alias set myminio "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

for BUCKET in lakehouse mlflow raw-data; do
  if mc ls "myminio/${BUCKET}" > /dev/null 2>&1; then
    echo "Bucket '${BUCKET}' already exists, skipping."
  else
    mc mb "myminio/${BUCKET}"
    echo "Bucket '${BUCKET}' created."
  fi
done

# ── Step 2: Create Polaris catalog ────────────────────────────────────
echo "Waiting for Polaris to be ready at ${POLARIS_URL}..."
until curl -s -o /dev/null -w "%{http_code}" "${POLARIS_URL}/api/catalog/v1/config" 2>/dev/null | grep -qE "^[2-4]"; do
  echo "  Polaris not ready yet, retrying in 5s..."
  sleep 5
done
echo "Polaris is ready!"

# Get OAuth2 token
echo "Obtaining OAuth2 token..."
TOKEN_RESPONSE=$(curl -s -X POST "${POLARIS_URL}/api/catalog/v1/oauth/tokens" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${POLARIS_CLIENT_ID}&client_secret=${POLARIS_CLIENT_SECRET}&scope=PRINCIPAL_ROLE:ALL" 2>&1)
echo "Token response: ${TOKEN_RESPONSE}"

# Extract access_token using sed (no python needed)
TOKEN=$(echo "$TOKEN_RESPONSE" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "ERROR: Could not obtain OAuth token from Polaris. Response was: ${TOKEN_RESPONSE}"
  echo "Check POLARIS_CLIENT_ID and POLARIS_CLIENT_SECRET match POLARIS_BOOTSTRAP_CREDENTIALS."
  exit 1
else
  echo "Token obtained successfully."
  AUTH_HEADER="Authorization: Bearer ${TOKEN}"
fi

# Create the lakehouse catalog
echo "Creating 'lakehouse' catalog..."
CATALOG_PAYLOAD=$(cat <<EOFPAYLOAD
{
  "name": "lakehouse",
  "type": "INTERNAL",
  "properties": {
    "default-base-location": "s3://lakehouse/",
    "s3.endpoint": "${MINIO_ENDPOINT}",
    "s3.path-style-access": "true",
    "s3.region": "us-east-1"
  },
  "storageConfigInfo": {
    "storageType": "S3",
    "allowedLocations": ["s3://lakehouse/"],
    "endpoint": "${MINIO_ENDPOINT}",
    "endpointInternal": "${MINIO_ENDPOINT}",
    "pathStyleAccess": true
  }
}
EOFPAYLOAD
)

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${POLARIS_URL}/api/management/v1/catalogs" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "$CATALOG_PAYLOAD")

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
  echo "Catalog 'lakehouse' created successfully."

  # Grant CATALOG_MANAGE_CONTENT to catalog_admin role (required for table operations)
  echo "Granting CATALOG_MANAGE_CONTENT to catalog_admin..."
  curl -s -o /dev/null -w "HTTP %{http_code}" -X PUT \
    "${POLARIS_URL}/api/management/v1/catalogs/lakehouse/catalog-roles/catalog_admin/grants" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -d '{"type":"catalog", "privilege":"CATALOG_MANAGE_CONTENT"}'
  echo ""

elif [ "$HTTP_CODE" = "409" ]; then
  echo "Catalog 'lakehouse' already exists, skipping."
else
  echo "Warning: Catalog creation returned HTTP ${HTTP_CODE}. You may need to create it manually."
fi

echo "Bootstrap complete."

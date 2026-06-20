#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="${ROOT_DIR}/terraform"
DASHBOARD_DIR="${ROOT_DIR}/dashboard"

cd "${TERRAFORM_DIR}"

API_URL="/api"
BUCKET="$(terraform output -raw dashboard_bucket_name)"
DISTRIBUTION_ID="$(terraform output -raw cloudfront_distribution_id)"

echo "Building dashboard with REACT_APP_API_URL=${API_URL}"
cd "${DASHBOARD_DIR}"
REACT_APP_API_URL="${API_URL}" npm run build

echo "Syncing build/ to s3://${BUCKET}/"
aws s3 sync build/ "s3://${BUCKET}/" --delete

echo "Invalidating CloudFront cache"
aws cloudfront create-invalidation \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/*"

echo "Dashboard deployed: $(terraform -chdir="${TERRAFORM_DIR}" output -raw cloudfront_url)"

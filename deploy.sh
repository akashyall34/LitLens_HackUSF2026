#!/bin/bash
# Re-deploy script — run this on EC2 after pushing new code to GitHub.
# Usage: bash deploy.sh

set -e

cd /home/ec2-user/litlens

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Refreshing secrets from SSM ==="
aws ssm get-parameters-by-path \
  --path /litlens/ \
  --with-decryption \
  --region us-east-1 \
  --query "Parameters[*].[Name,Value]" \
  --output text \
  | awk '{gsub("/litlens/","",$1); print toupper($1)"="$2}' > .env

# FRONTEND_ORIGIN must be a real SPA URL in SSM (e.g. https://….vercel.app), not *.

echo "=== Restarting stack ==="
docker compose -f docker-compose.prod.yml up -d --build

echo "=== Deploy complete ==="
docker compose -f docker-compose.prod.yml ps

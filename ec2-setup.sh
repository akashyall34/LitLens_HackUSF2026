#!/bin/bash
# EC2 initial setup script — run this once after SSHing into a fresh Amazon Linux 2023 instance.
# Usage: bash ec2-setup.sh

set -e

echo "=== Installing Docker ==="
dnf update -y
dnf install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

echo "=== Installing Docker Compose plugin ==="
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "=== Cloning repository ==="
cd /home/ec2-user
git clone https://github.com/akashyall34/LitLens_HackUSF2026 litlens
chown -R ec2-user:ec2-user litlens

echo "=== Pulling secrets from SSM into .env ==="
cd /home/ec2-user/litlens
aws ssm get-parameters-by-path \
  --path /litlens/ \
  --with-decryption \
  --region us-east-1 \
  --query "Parameters[*].[Name,Value]" \
  --output text \
  | awk '{gsub("/litlens/","",$1); print toupper($1)"="$2}' > .env

# Append any vars not in SSM
echo "FRONTEND_ORIGIN=*" >> .env

echo "=== Starting production stack ==="
docker compose -f docker-compose.prod.yml up -d --build

echo "=== Done! Check status with: docker compose -f docker-compose.prod.yml ps ==="

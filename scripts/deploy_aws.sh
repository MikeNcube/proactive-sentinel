#!/bin/bash
# Proactive Sentinel — AWS deployment script
# Run this to build, push, and deploy to AWS App Runner
# Requires: AWS CLI configured, Docker running, Terraform installed

set -euo pipefail

REGION="af-south-1"
ECR_REPO="proactive-sentinel"
IMAGE_TAG=$(git rev-parse --short HEAD)
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

if [[ -z "${DATABASE_URL:-}" || -z "${SECRET_KEY:-}" || -z "${JWT_SECRET_KEY:-}" ]]; then
  echo "DATABASE_URL, SECRET_KEY, and JWT_SECRET_KEY must be set in environment."
  exit 1
fi

echo "Starting deployment for commit ${IMAGE_TAG}"

echo "Running tests..."
PYTHONPATH=. pytest tests/ --tb=short -q
echo "Tests passed"

echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${REGION}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${ECR_REPO}" --region "${REGION}" >/dev/null

echo "Building Docker image..."
docker build -t "${ECR_REPO}:${IMAGE_TAG}" .
echo "Build complete"

echo "Logging into ECR..."
aws ecr get-login-password --region "${REGION}" | \
  docker login --username AWS \
  --password-stdin "${AWS_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

echo "Pushing image..."
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:latest"
docker push "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:latest"
echo "Image pushed: ${ECR_URI}:${IMAGE_TAG}"

echo "Running Terraform..."
cd infrastructure/
terraform init
terraform apply \
  -var="image_uri=${ECR_URI}:${IMAGE_TAG}" \
  -var="database_url=${DATABASE_URL}" \
  -var="secret_key=${SECRET_KEY}" \
  -var="jwt_secret_key=${JWT_SECRET_KEY}" \
  -auto-approve

SERVICE_URL=$(terraform output -raw service_url)
echo "Deployment complete"
echo "Service URL: https://${SERVICE_URL}"

echo "Running health check..."
sleep 30
curl -f "https://${SERVICE_URL}/health" && echo "Health check passed"

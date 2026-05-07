# Proactive Sentinel — AWS deployment script (PowerShell)
# Run this on Windows to build and deploy to AWS

$ErrorActionPreference = "Stop"

$Region = "af-south-1"
$EcrRepo = "proactive-sentinel"
$ImageTag = (git rev-parse --short HEAD).Trim()
$AwsAccount = (aws sts get-caller-identity --query Account --output text).Trim()
$EcrUri = "$AwsAccount.dkr.ecr.$Region.amazonaws.com/$EcrRepo"

if (-not $env:DATABASE_URL -or -not $env:SECRET_KEY -or -not $env:JWT_SECRET_KEY) {
  throw "DATABASE_URL, SECRET_KEY, and JWT_SECRET_KEY environment variables are required."
}

Write-Host "Starting deployment for commit $ImageTag"

Write-Host "Running tests..."
$env:PYTHONPATH = "."
pytest tests/ --tb=short -q
Write-Host "Tests passed"

Write-Host "Ensuring ECR repository exists..."
try {
  aws ecr describe-repositories --repository-names $EcrRepo --region $Region | Out-Null
}
catch {
  aws ecr create-repository --repository-name $EcrRepo --region $Region | Out-Null
}

Write-Host "Building Docker image..."
docker build -t "${EcrRepo}:${ImageTag}" .

Write-Host "Logging into ECR..."
aws ecr get-login-password --region $Region |
  docker login --username AWS --password-stdin `
  "$AwsAccount.dkr.ecr.$Region.amazonaws.com"

Write-Host "Pushing image to ECR..."
docker tag "${EcrRepo}:${ImageTag}" "${EcrUri}:${ImageTag}"
docker tag "${EcrRepo}:${ImageTag}" "${EcrUri}:latest"
docker push "${EcrUri}:${ImageTag}"
docker push "${EcrUri}:latest"

Write-Host "Running Terraform..."
Set-Location infrastructure/
terraform init
terraform apply `
  -var="image_uri=${EcrUri}:${ImageTag}" `
  -var="database_url=$env:DATABASE_URL" `
  -var="secret_key=$env:SECRET_KEY" `
  -var="jwt_secret_key=$env:JWT_SECRET_KEY" `
  -auto-approve

$ServiceUrl = terraform output -raw service_url
Write-Host "Deployment complete"
Write-Host "Service URL: https://$ServiceUrl"

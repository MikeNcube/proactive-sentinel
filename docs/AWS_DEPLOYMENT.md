# AWS Deployment Guide — Proactive Sentinel

Deploys to **AWS App Runner** in `af-south-1` (Cape Town). Container image is stored in ECR; secrets in Secrets Manager; state in S3 with DynamoDB lock.

---

## Prerequisites

| Tool | Version |
|------|---------|
| AWS CLI | 2.x, configured with `aws configure` |
| Docker | 24+ |
| Terraform | 1.7+ |
| Python | 3.11+ |

The IAM identity used must have permissions for: ECR (push), Secrets Manager (create/update), App Runner (create/update), IAM (create roles), S3 (state bucket).

---

## One-time setup

### 1. Create the Terraform state bucket

```bash
aws s3api create-bucket \
  --bucket zororo-terraform-state \
  --region af-south-1 \
  --create-bucket-configuration LocationConstraint=af-south-1

aws s3api put-bucket-versioning \
  --bucket zororo-terraform-state \
  --versioning-configuration Status=Enabled
```

### 2. Create the DynamoDB lock table

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region af-south-1
```

---

## Deployment

### Linux / macOS

```bash
export DATABASE_URL="postgresql://user:password@host:5432/sentinel"
export SECRET_KEY="$(openssl rand -hex 32)"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"

chmod +x scripts/deploy_aws.sh
./scripts/deploy_aws.sh
```

### Windows (PowerShell)

```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/sentinel"
$env:SECRET_KEY   = -join ((65..90 + 97..122 + 48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
$env:JWT_SECRET_KEY = -join ((65..90 + 97..122 + 48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})

.\scripts\deploy_aws.ps1
```

The script will:

1. Run all pytest tests — aborts on failure
2. Build the Docker image tagged with the current git commit SHA
3. Push the image to ECR (creates the repository if it does not exist)
4. Run `terraform apply` to provision/update all AWS resources
5. Print the App Runner service URL
6. Run a `/health` check against the live URL

---

## What Terraform provisions

| Resource | Name |
|----------|------|
| ECR repository | `proactive-sentinel` |
| Secrets Manager secret | `sentinel/production/database_url` |
| Secrets Manager secret | `sentinel/production/secret_key` |
| Secrets Manager secret | `sentinel/production/jwt_secret_key` |
| IAM role (ECR access) | `proactive-sentinel-apprunner-ecr-access-production` |
| IAM role (instance) | `proactive-sentinel-apprunner-instance-production` |
| App Runner service | `proactive-sentinel-production` |

The App Runner service injects all three secrets as environment variables. `JWT_SECRET_KEY` is required at startup — the application throws `RuntimeError` if it is absent.

---

## Rotating secrets

```bash
# Generate a new JWT secret
NEW_SECRET=$(openssl rand -hex 32)

# Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id sentinel/production/jwt_secret_key \
  --secret-string "$NEW_SECRET" \
  --region af-south-1

# Re-apply Terraform to pick up the new ARN reference
export JWT_SECRET_KEY="$NEW_SECRET"
cd infrastructure/
terraform apply \
  -var="image_uri=$(terraform output -raw service_url)" \
  -var="database_url=$DATABASE_URL" \
  -var="secret_key=$SECRET_KEY" \
  -var="jwt_secret_key=$JWT_SECRET_KEY" \
  -auto-approve
```

Then trigger an App Runner redeployment so running instances pick up the new secret:

```bash
SERVICE_ARN=$(aws apprunner list-services --region af-south-1 \
  --query "ServiceSummaryList[?ServiceName=='proactive-sentinel-production'].ServiceArn" \
  --output text)

aws apprunner start-deployment \
  --service-arn "$SERVICE_ARN" \
  --region af-south-1
```

---

## Tearing down

```bash
cd infrastructure/
terraform destroy \
  -var="image_uri=dummy" \
  -var="database_url=dummy" \
  -var="secret_key=dummy" \
  -var="jwt_secret_key=dummy" \
  -auto-approve
```

This removes all App Runner, IAM, and Secrets Manager resources. The ECR repository and its images are also destroyed. The S3 state bucket and DynamoDB lock table are not managed by this Terraform configuration and must be deleted manually if no longer needed.

---

## Health check

```
GET /health
→ {"status": "healthy", "database": "reachable"}
```

App Runner polls `/health` every 20 seconds with a 5-second timeout. Two consecutive failures trigger a container replacement.

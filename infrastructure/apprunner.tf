# Proactive Sentinel — AWS App Runner deployment
# Low cost, auto-scaling, no EC2 management needed
# Free tier: 25 hours/month for ARM builds

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "zororo-terraform-state"
    key    = "proactive-sentinel/terraform.tfstate"
    region = "af-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "af-south-1"
}

variable "environment" {
  default = "production"
}

variable "image_uri" {
  description = "ECR image URI for the Sentinel container"
}

variable "database_url" {
  description = "PostgreSQL connection string"
  sensitive   = true
}

variable "secret_key" {
  description = "Application secret key for JWT"
  sensitive   = true
}

resource "aws_ecr_repository" "sentinel" {
  name                 = "proactive-sentinel"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = "proactive-sentinel"
    Environment = var.environment
    Owner       = "Mike S Ncube"
  }
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "sentinel/${var.environment}/database_url"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = var.database_url
}

resource "aws_secretsmanager_secret" "secret_key" {
  name = "sentinel/${var.environment}/secret_key"
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = var.secret_key
}

resource "aws_iam_role" "apprunner_ecr_access_role" {
  name = "proactive-sentinel-apprunner-ecr-access-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_policy" {
  role       = aws_iam_role.apprunner_ecr_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "apprunner_instance_role" {
  name = "proactive-sentinel-apprunner-instance-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "apprunner_secrets_access" {
  name = "proactive-sentinel-apprunner-secrets-${var.environment}"
  role = aws_iam_role.apprunner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database_url.arn,
          aws_secretsmanager_secret.secret_key.arn
        ]
      }
    ]
  })
}

resource "aws_apprunner_service" "sentinel" {
  service_name = "proactive-sentinel-${var.environment}"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access_role.arn
    }

    image_repository {
      image_identifier      = var.image_uri
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          ENVIRONMENT = var.environment
          PYTHONPATH  = "/app"
        }
        runtime_environment_secrets = {
          DATABASE_URL = aws_secretsmanager_secret.database_url.arn
          SECRET_KEY   = aws_secretsmanager_secret.secret_key.arn
        }
      }
    }
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = "0.25 vCPU"
    memory            = "0.5 GB"
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  health_check_configuration {
    path     = "/health"
    protocol = "HTTP"
    interval = 20
    timeout  = 5
  }

  tags = {
    Project     = "proactive-sentinel"
    Environment = var.environment
  }
}

output "service_url" {
  value = aws_apprunner_service.sentinel.service_url
}

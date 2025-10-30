# ECR Repository for Parser Lambda
resource "aws_ecr_repository" "parser" {
  name                 = "${var.project_name}-parser"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-parser-ecr"
      Description = "Container images for campaign brief parser Lambda"
    }
  )
}

# Lifecycle policy for parser
resource "aws_ecr_lifecycle_policy" "parser" {
  repository = aws_ecr_repository.parser.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository for Generator Lambda
resource "aws_ecr_repository" "generator" {
  name                 = "${var.project_name}-generator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-generator-ecr"
      Description = "Container images for AI image generator Lambda"
    }
  )
}

# Lifecycle policy for generator
resource "aws_ecr_lifecycle_policy" "generator" {
  repository = aws_ecr_repository.generator.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository for Variants Lambda
resource "aws_ecr_repository" "variants" {
  name                 = "${var.project_name}-variants"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-variants-ecr"
      Description = "Container images for variants generator Lambda"
    }
  )
}

# Lifecycle policy for variants
resource "aws_ecr_lifecycle_policy" "variants" {
  repository = aws_ecr_repository.variants.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

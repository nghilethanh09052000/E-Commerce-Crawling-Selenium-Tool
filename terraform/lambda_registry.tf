resource "aws_ecr_repository" "specific_scraper_lambda_production" {
  name                 = "specific-scraper-lambda-production"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}


resource "aws_ecr_repository" "get_ip_lambda_production" {
  name                 = "get-ip-lambda-production"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}

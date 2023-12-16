resource "aws_ecr_repository" "specific_scraper_production" {
  name                 = "specific-scraper-production"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}

locals {
    specific_scraper_production_repository_name = aws_ecr_repository.specific_scraper_production.repository_url
}

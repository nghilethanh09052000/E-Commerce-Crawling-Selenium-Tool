resource "aws_ecs_cluster" "specific_scraper" {
  name = "specific-scraper"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
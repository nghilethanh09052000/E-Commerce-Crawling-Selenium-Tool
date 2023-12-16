resource "aws_ecs_task_definition" "specific_scraper" {
  family                   = "specific-scraper"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  memory                   = 1024
  cpu                      = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "specific-scraper-production"
      image     = "${local.specific_scraper_production_repository_name}:latest"
      cpu       = 0
      essential = true
      command = [
        "python3"
      ]
      environment = [
        {
          "name" : "PYTHONPATH",
          "value" : "."
        }
      ]
      linuxParameters = {
        "initProcessEnabled": true
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group" : "${aws_cloudwatch_log_group.specific_scraper.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/specific_scraper"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "specific-scraper"
  }
}

resource "aws_cloudwatch_log_group" "specific_scraper" {
  name              = "/aws/ecs/specific_scraper"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "specific-scraper"
  }
}

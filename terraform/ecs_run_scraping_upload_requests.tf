resource "aws_ecs_task_definition" "run_scraping_upload_requests" {
  family                   = "run-scraping-upload-requests"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  memory                   = 2048
  cpu                      = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "specific-scraper-production"
      image     = "${local.specific_scraper_production_repository_name}:latest"
      cpu       = 0
      essential = true
      command = [
        "python3",
        "cronjobs/run_scraping_upload_requests.py"
      ]
      environment = [
        {
          "name" : "PYTHONPATH",
          "value" : "."
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group" : "${aws_cloudwatch_log_group.run_scraping_upload_requests.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/run_scraping_upload_requests"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "run-scraping-upload-requests"
  }
}

resource "aws_cloudwatch_log_group" "run_scraping_upload_requests" {
  name              = "/aws/ecs/run_scraping_upload_requests"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "run-scraping-upload-requests"
  }
}

resource "aws_cloudwatch_event_rule" "run_scraping_upload_requests" {
  name                = "run-scraping-upload-requests"
  schedule_expression = "cron(0/5 * * * ? *)"
  description         = "Every 5 minutes, launch the upload request tasks that need to be executed"
}

resource "aws_cloudwatch_event_target" "run_scraping_upload_requests" {
  target_id = "run-scraping-upload-requests"
  arn       = aws_ecs_cluster.specific_scraper.arn
  rule      = aws_cloudwatch_event_rule.run_scraping_upload_requests.name
  role_arn  = aws_iam_role.ecs_events_role.arn

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.run_scraping_upload_requests.arn

    network_configuration {
      subnets          = [local.public_subnet_id]
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

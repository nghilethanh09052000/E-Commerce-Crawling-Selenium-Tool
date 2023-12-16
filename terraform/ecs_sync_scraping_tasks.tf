resource "aws_ecs_task_definition" "sync_scraping_tasks" {
  family                   = "sync-scraping-tasks"
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
        "cronjobs/sync_scraping_tasks.py"
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
          "awslogs-group" : "${aws_cloudwatch_log_group.sync_scraping_tasks.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/sync_scraping_tasks"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "sync-scraping-tasks"
  }
}

resource "aws_cloudwatch_log_group" "sync_scraping_tasks" {
  name              = "/aws/ecs/sync_scraping_tasks"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "sync-scraping-tasks"
  }
}

resource "aws_cloudwatch_event_rule" "sync_scraping_tasks" {
  name                = "sync-scraping-tasks"
  schedule_expression = "cron(0 1 * * ? *)"
  description         = "Every day at 1:00, sync specific scraper db with counterfeit db"
}

resource "aws_cloudwatch_event_target" "sync_scraping_tasks" {
  target_id = "sync-scraping-tasks"
  arn       = aws_ecs_cluster.specific_scraper.arn
  rule      = aws_cloudwatch_event_rule.sync_scraping_tasks.name
  role_arn  = aws_iam_role.ecs_events_role.arn

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sync_scraping_tasks.arn

    network_configuration {
      subnets          = [local.public_subnet_id]
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

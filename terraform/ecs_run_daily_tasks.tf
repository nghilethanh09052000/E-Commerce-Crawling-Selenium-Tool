resource "aws_ecs_task_definition" "run_daily_tasks" {
  family                   = "run-daily-tasks"
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
        "cronjobs/run_daily_tasks.py"
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
          "awslogs-group" : "${aws_cloudwatch_log_group.run_daily_tasks.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/run_daily_tasks"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "run-daily-tasks"
  }
}

resource "aws_cloudwatch_log_group" "run_daily_tasks" {
  name              = "/aws/ecs/run_daily_tasks"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "run-daily-tasks"
  }
}

resource "aws_cloudwatch_event_rule" "run_daily_tasks" {
  name                = "run-daily-tasks"
  schedule_expression = "cron(0,15,30,45 * * * ? *)"
  description         = "Every 15 minutes, check if a scraping task needs to be executed"
}

resource "aws_cloudwatch_event_target" "run_daily_tasks" {
  target_id = "run-daily-tasks"
  arn       = aws_ecs_cluster.specific_scraper.arn
  rule      = aws_cloudwatch_event_rule.run_daily_tasks.name
  role_arn  = aws_iam_role.ecs_events_role.arn
  input     = jsonencode({})

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.run_daily_tasks.arn

    network_configuration {
      subnets          = [local.public_subnet_id]
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

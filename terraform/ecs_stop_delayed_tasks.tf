resource "aws_ecs_task_definition" "stop_delayed_tasks" {
  family                   = "stop-delayed-tasks"
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
        "cronjobs/stop_delayed_tasks.py"
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
          "awslogs-group" : "${aws_cloudwatch_log_group.stop_delayed_tasks.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/stop_delayed_tasks"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "stop-delayed-tasks"
  }
}

resource "aws_cloudwatch_log_group" "stop_delayed_tasks" {
  name              = "/aws/ecs/stop_delayed_tasks"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "stop-delayed-tasks"
  }
}

resource "aws_cloudwatch_event_rule" "stop_delayed_tasks" {
  name                = "stop-delayed-tasks"
  schedule_expression = "cron(0 /1 * * ? *)"
  description         = "Runs every 1 hours to stop tasks than run for more than one day"
}

resource "aws_cloudwatch_event_target" "stop_delayed_tasks" {
  target_id = "stop-delayed-tasks"
  arn       = aws_ecs_cluster.specific_scraper.arn
  rule      = aws_cloudwatch_event_rule.stop_delayed_tasks.name
  role_arn  = aws_iam_role.ecs_events_role.arn

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.stop_delayed_tasks.arn

    network_configuration {
      subnets          = [local.public_subnet_id]
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

resource "aws_ecs_task_definition" "run_recrawling_posts" {
  family                   = "run-recrawling-posts"
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
        "cronjobs/run_recrawling_posts.py"
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
          "awslogs-group" : "${aws_cloudwatch_log_group.run_recrawling_posts.name}",
          "awslogs-region" : "eu-west-1",
          "awslogs-stream-prefix" : "ecs/run_recrawling_posts"
        }
      }
    },
  ])

  runtime_platform {
    operating_system_family = "LINUX"
  }

  tags = {
    Module = "EcsTasks"
    Name   = "run-recrawling-posts"
  }
}

resource "aws_cloudwatch_log_group" "run_recrawling_posts" {
  name              = "/aws/ecs/run_recrawling_posts"
  retention_in_days = 180

  tags = {
    Module = "NetworkOnlyTasks"
    Name   = "run-recrawling-posts"
  }
}

resource "aws_cloudwatch_event_rule" "run_recrawling_posts" {
  name                = "run-recrawling-posts"
  schedule_expression = "cron(0 /2 * * ? *)"
  description         = "Every 2 hours checks posts to be recrawled from rise results"
}

resource "aws_cloudwatch_event_target" "run_recrawling_posts" {
  target_id = "run-recrawling-posts"
  arn       = aws_ecs_cluster.specific_scraper.arn
  rule      = aws_cloudwatch_event_rule.run_recrawling_posts.name
  role_arn  = aws_iam_role.ecs_events_role.arn

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.run_recrawling_posts.arn

    network_configuration {
      subnets          = [local.public_subnet_id]
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

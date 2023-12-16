resource "aws_db_subnet_group" "specific-scraper" {
  name       = "specific-scraper"
  subnet_ids = [aws_subnet.private_main.id, aws_subnet.private_secondary.id]

  tags = {
    Module = "Storage"
    Name = "rds"
  }
}

resource "aws_db_instance" "specific-scraper" {
  identifier                   = "specific-scraper"
  engine                       = "postgres"
  engine_version               = "14.7"
  instance_class               = "db.t3.large"
  allocated_storage            = 100
  max_allocated_storage        = 500
  username                     = "postgres"
  password                     = var.DB_PWD
  parameter_group_name         = aws_db_parameter_group.specific-scraper.name
  db_subnet_group_name         = aws_db_subnet_group.specific-scraper.name
  multi_az                     = false
  availability_zone            = var.default_az
  skip_final_snapshot          = false
  final_snapshot_identifier    = "specific-scraper-${replace(timestamp(), ":", "-")}"
  vpc_security_group_ids       = [aws_security_group.specific_scraper_db.id]
  storage_encrypted            = true
  performance_insights_enabled = true
  backup_retention_period      = 14
  maintenance_window           = "Mon:15:00-Mon:16:00"

  tags = {
    Module = "Storage"
    Name   = "rds"
  }

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      backup_retention_period,
      iops,
      monitoring_interval,
    ]
  }
}

resource "aws_db_parameter_group" "specific-scraper" {
  name   = "specific-scraper"
  family = "postgres14"

  parameter {
    name  = "log_autovacuum_min_duration"
    value = "1000"
  }

  parameter {
    apply_method = "pending-reboot"
    name = "max_connections"
    value = "2000"
  }
}
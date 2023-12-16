module "worker_scraping" {
  source                   = "./worker"
  environment_name         = "production"
  name                     = "scraping"
  subnet_id                = aws_subnet.public_main.id
  beanstalk_instance_types = "t3.2xlarge, t2.2xlarge"
  beanstalk_profile        = aws_iam_instance_profile.beanstalk.id
  security_group           = aws_security_group.worker.id
  instance_volume_size     = var.instance_volume_size
  scaling_adjustment       = 1
  min_number_of_instances  = 1
  max_number_of_instances  = 6
  max_connection           = 15
  connection_timeout       = 600
  sqs_alarm_low_threshold  = 200
  sqs_alarm_high_threshold = 500
}

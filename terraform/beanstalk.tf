resource "aws_elastic_beanstalk_application" "navee_driver" {
  name = "navee-driver"

  tags = {
    Module = "NaveeDriver"
  }
}

resource "aws_elastic_beanstalk_application_version" "navee_driver" {
  name        = "navee-driver"
  application = aws_elastic_beanstalk_application.navee_driver.id
  bucket      = aws_s3_bucket.docker_images_navee_driver.bucket
  key         = "navee-driver.production.zip"

  tags = {
    Module = "NaveeDriver"
  }
}

resource "aws_elastic_beanstalk_environment" "navee_driver" {
  name                = "navee-driver"
  application         = aws_elastic_beanstalk_application.navee_driver.name
  solution_stack_name = data.aws_elastic_beanstalk_solution_stack.docker.name
  version_label       = aws_elastic_beanstalk_application_version.navee_driver.id

  # Two workarounds for the "perpetual diff" when applying terraform:
  #   1. resource  = ""
  #   2. sorting the subnets list
  # see https://github.com/hashicorp/terraform/issues/22563
  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = join(",", sort([aws_subnet.public_main.id,aws_subnet.public_secondary.id]))
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile.beanstalk.id
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = aws_security_group.navee_driver.id
    resource  = ""
  }

  setting {
    namespace = "aws:ec2:instances"
    name      = "InstanceTypes"
    value     = "t3.2xlarge"
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment:process:default"
    name      = "HealthCheckPath"
    value     = "/api/health_check"
    resource  = ""
  }

  # Deployment policy
  setting {
    namespace = "aws:elasticbeanstalk:command"
    name      = "DeploymentPolicy"
    value     = "Immutable"
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:updatepolicy:rollingupdate"
    name      = "RollingUpdateEnabled"
    value     = "true"
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:updatepolicy:rollingupdate"
    name      = "RollingUpdateType"
    value     = "Immutable"
    resource  = ""
  }

  # HTTPS
  setting {
    namespace = "aws:elbv2:listener:443"
    name      = "Protocol"
    value     = "HTTPS"
    resource  = ""
  }

  setting {
    namespace = "aws:elbv2:listener:443"
    name      = "SSLCertificateArns"
    value     = aws_acm_certificate.navee_driver.id
    resource  = ""
  }

  setting {
    namespace = "aws:elbv2:listener:443"
    name      = "SSLPolicy"
    value     = "ELBSecurityPolicy-FS-1-1-2019-08"
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "LoadBalancerType"
    value     = "application"
    resource  = ""
  }

  # Autoscaling
  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MinSize"
    value     = 5
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MaxSize"
    value     = var.max_number_of_instance
    resource  = ""
  }

  # Logs
  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "RetentionInDays"
    value     = "180"
    resource  = ""
  }

  # Use spot instances
  setting {
    namespace = "aws:ec2:instances"
    name      = "EnableSpot"
    value     = "true"
    resource  = ""
  }

  setting {
    namespace = "aws:ec2:instances"
    name      = "SpotFleetOnDemandAboveBasePercentage"
    value     = "0"
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "EnableCapacityRebalancing"
    value     = "true"
    resource  = ""
  }

  # Additional storage
  dynamic "setting" {
    for_each = var.instance_volume_size != null ? [1] : []
    content {
      namespace = "aws:autoscaling:launchconfiguration"
      name      = "RootVolumeType"
      value     = "gp2"
      resource  = ""
    }
  }

  dynamic "setting" {
    for_each = var.instance_volume_size != null ? [1] : []
    content {
      namespace = "aws:autoscaling:launchconfiguration"
      name      = "RootVolumeSize"
      value     = var.instance_volume_size
      resource  = ""
    }
  }

  tags = {
    Module = "NaveeDriver"
  }

  lifecycle {
    ignore_changes = [
      version_label,
      solution_stack_name
    ]
  }
}

data "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_elastic_beanstalk_environment.navee_driver.load_balancers[0]
  port              = 80
}

resource "aws_lb_listener_rule" "redirect_http_to_https" {
  listener_arn = data.aws_lb_listener.http_listener.arn
  priority     = 1

  action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}

data "aws_elastic_beanstalk_solution_stack" "docker" {
  most_recent = true
  name_regex  = "^64bit Amazon Linux 2 (.*) running Docker$"
}

resource "aws_elastic_beanstalk_application" "worker" {
  name = "scraping-worker"

  appversion_lifecycle {
    service_role          = "arn:aws:iam::068631914562:role/aws-service-role/elasticbeanstalk.amazonaws.com/AWSServiceRoleForElasticBeanstalk"
    max_count             = 99
    delete_source_from_s3 = true
  }

  tags = {
    Module = "Worker"
  }
}

resource "aws_elastic_beanstalk_application_version" "worker" {
  name        = "scraping-worker"
  application = aws_elastic_beanstalk_application.worker.id
  bucket      = var.docker_bucket
  key         = "scraping-worker.production.zip"

  tags = {
    Module = "Worker"
  }
}

# The 'resorce = ""' lines below are a workaround for false diffs.
# See https://github.com/hashicorp/terraform/issues/22563

resource "aws_elastic_beanstalk_environment" "worker" {
  name                = "scraping-worker"
  application         = aws_elastic_beanstalk_application.worker.name
  solution_stack_name = data.aws_elastic_beanstalk_solution_stack.docker.name
  version_label       = aws_elastic_beanstalk_application_version.worker.id
  tier                = "Worker"

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = var.subnet_id
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = var.beanstalk_profile
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = var.security_group
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:sqsd"
    name      = "WorkerQueueURL"
    value     = aws_sqs_queue.queue_main.id
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MinSize"
    value     = var.min_number_of_instances
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MaxSize"
    value     = var.max_number_of_instances
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:sqsd"
    name      = "InactivityTimeout"
    value     = var.connection_timeout
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:sqsd"
    name      = "HttpConnections"
    value     = var.max_connection
    resource  = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:sqsd"
    name      = "MaxRetries"
    value     = 1
    resource  = ""
  }

  # TEMP
  setting {
    namespace = "aws:elasticbeanstalk:environment:proxy"
    name      = "ProxyServer"
    value     = "none"
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

  # Deployment policy
  dynamic "setting" {
    for_each = var.immutable_deployment == "true" ? [1] : []
    content {
      namespace = "aws:elasticbeanstalk:command"
      name      = "DeploymentPolicy"
      value     = "RollingWithAdditionalBatch"
      resource  = ""
    }
  }

  dynamic "setting" {
    for_each = var.immutable_deployment == "true" ? [1] : []
    content {
      namespace = "aws:autoscaling:updatepolicy:rollingupdate"
      name      = "RollingUpdateEnabled"
      value     = "true"
      resource  = ""
    }
  }

  dynamic "setting" {
    for_each = var.immutable_deployment == "true" ? [1] : []
    content {
      namespace = "aws:elasticbeanstalk:command"
      name      = "BatchSizeType"
      value     = "Fixed"
      resource  = ""
    }
  }

  dynamic "setting" {
    for_each = var.immutable_deployment == "true" ? [1] : []
    content {
      namespace = "aws:elasticbeanstalk:command"
      name      = "BatchSize"
      value     = "10"
      resource  = ""
    }
  }

  dynamic "setting" {
    for_each = var.immutable_deployment == "true" ? [1] : []
    content {
      namespace = "aws:autoscaling:updatepolicy:rollingupdate"
      name      = "RollingUpdateType"
      value     = "Time"
      resource  = ""
    }
  }

  # Visibility Timeout
  setting {
    namespace = "aws:elasticbeanstalk:sqsd"
    name = "VisibilityTimeout"
    value     = 650
    resource  = ""
  }

  # Logs
  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
    resource  = ""
  }

  # Use spot instances
  setting {
    namespace = "aws:ec2:instances"
    name      = "EnableSpot"
    value     = "true"
    resource  = ""
  }

  # The initial instance should always be on demand
  setting {
    namespace = "aws:ec2:instances"
    name      = "SpotFleetOnDemandBase"
    value     = "1"
    resource  = ""
  }

  # All the next instances created when scaling up should be spot instances
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

  setting {
    namespace = "aws:ec2:instances"
    name      = "InstanceTypes"
    value     = var.beanstalk_instance_types
    resource  = ""
  }

  # Disable alarms
  setting {
    namespace = "aws:autoscaling:trigger"
    name      = "LowerThreshold"
    value     = "0"
    resource  = ""
  }

  setting {
    namespace = "aws:autoscaling:trigger"
    name      = "UpperThreshold"
    value     = "20000000"
    resource  = ""
  }

  # Deployment timeout
  setting {
    namespace = "aws:elasticbeanstalk:command"
    name      = "Timeout"
    value     = "1800"
    resource  = ""
  }


  tags = {
    Module = "Worker"
  }

  lifecycle {
    ignore_changes = [
      version_label,
      solution_stack_name
    ]
  }
}

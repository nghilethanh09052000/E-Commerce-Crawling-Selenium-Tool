resource "aws_cloudwatch_metric_alarm" "worker_queue_size_alarm_low" {
  alarm_name          = "scraping-worker-queue-size-alarm-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  threshold           = var.sqs_alarm_low_threshold

  metric_query {
    id          = "m1"
    label       = "Scale down when queue has less than n messages"
    return_data = true

    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesVisible"
      period      = 10
      stat        = "Maximum"

      dimensions = {
        QueueName = aws_sqs_queue.queue_main.name
      }
    }
  }

  alarm_actions = [aws_autoscaling_policy.worker_scale_down.arn]
}


resource "aws_autoscaling_policy" "worker_scale_down" {
  name                   = "scraping-worker-queue-size-alarm-low"
  scaling_adjustment     = var.min_number_of_instances
  adjustment_type        = "ExactCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_elastic_beanstalk_environment.worker.autoscaling_groups[0]
}


resource "aws_cloudwatch_metric_alarm" "worker_queue_size_alarm_high" {
  alarm_name          = "scraping-worker-queue-size-alarm-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = var.sqs_alarm_high_threshold

  metric_query {
    id          = "m1"
    label       = "Scale up when queue has more than n messages"
    return_data = true

    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesVisible"
      period      = 10
      stat        = "Maximum"

      dimensions = {
        QueueName = aws_sqs_queue.queue_main.name
      }
    }
  }

  alarm_actions = [aws_autoscaling_policy.worker_scale_up.arn]
}


resource "aws_autoscaling_policy" "worker_scale_up" {
  name                   = "scraping-worker-queue-size-alarm-high"
  scaling_adjustment     = var.scaling_adjustment
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_elastic_beanstalk_environment.worker.autoscaling_groups[0]
}

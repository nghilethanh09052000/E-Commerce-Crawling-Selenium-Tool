resource "aws_sqs_queue" "queue_main" {
  name                       = "scraping-worker-main"
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = var.connection_timeout
  sqs_managed_sse_enabled    = false

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.queue_deadletter.arn
    maxReceiveCount     = 1
  })

  tags = {
    Module = "Worker"
  }
}

resource "aws_sqs_queue" "queue_deadletter" {
  name                       = "scraping-worker-deadletter"
  visibility_timeout_seconds = 600
  message_retention_seconds  = 1209600
  sqs_managed_sse_enabled    = false

  tags = {
    Module = "Worker"
  }
}

# Lambda
resource "aws_lambda_permission" "ip_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ip_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.ip_lambda.execution_arn}/*/*"
}

resource "aws_lambda_function" "ip_lambda" {
  image_uri     = "${aws_ecr_repository.get_ip_lambda_production.repository_url}:latest"
  function_name = "ip-lambda"
  role          = aws_iam_role.iam_for_lambda.arn
  package_type  = "Image"
  timeout       = 30
  memory_size   = 2048

  vpc_config {
    subnet_ids         = [aws_subnet.public_main.id]
    security_group_ids = [aws_security_group.ecs.id]
  }

  tags = {
    Name = "ip-lambda"
  }
}


# API Gateway
resource "aws_apigatewayv2_api" "ip_lambda" {
  name          = "ip-lambda"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "ip_lambda" {
  api_id = aws_apigatewayv2_api.ip_lambda.id

  name        = "ip-lambda"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.ip_lambda_api_gw.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

resource "aws_apigatewayv2_integration" "ip_lambda" {
  api_id = aws_apigatewayv2_api.ip_lambda.id

  integration_uri        = aws_lambda_function.ip_lambda.invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "ip_lambda" {
  api_id             = aws_apigatewayv2_api.ip_lambda.id
  route_key          = "$default"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.ip_lambda.id}"
}

resource "aws_cloudwatch_log_group" "ip_lambda_api_gw" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.ip_lambda.name}"

  retention_in_days = 180
}

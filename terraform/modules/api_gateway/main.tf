data "aws_region" "current" {}

resource "aws_api_gateway_rest_api" "api" {
  name        = var.api_name
  description = "RecallRadar REST API for recall queries"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "recalls" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "recalls"
}

resource "aws_api_gateway_resource" "recalls_stats" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.recalls.id
  path_part   = "stats"
}

resource "aws_api_gateway_resource" "recalls_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.recalls.id
  path_part   = "{recall_number}"
}

locals {
  routes = {
    recalls = {
      resource_id = aws_api_gateway_resource.recalls.id
      path        = "/recalls"
    }
    recalls_stats = {
      resource_id = aws_api_gateway_resource.recalls_stats.id
      path        = "/recalls/stats"
    }
    recalls_id = {
      resource_id = aws_api_gateway_resource.recalls_id.id
      path        = "/recalls/{recall_number}"
    }
  }
}

resource "aws_api_gateway_method" "get" {
  for_each = local.routes

  rest_api_id      = aws_api_gateway_rest_api.api.id
  resource_id      = each.value.resource_id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_method" "options" {
  for_each = local.routes

  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = each.value.resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_lambda" {
  for_each = local.routes

  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = each.value.resource_id
  http_method             = aws_api_gateway_method.get[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

resource "aws_api_gateway_integration" "options_lambda" {
  for_each = local.routes

  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = each.value.resource_id
  http_method             = aws_api_gateway_method.options[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.recalls.id,
      aws_api_gateway_resource.recalls_stats.id,
      aws_api_gateway_resource.recalls_id.id,
      aws_api_gateway_method.get,
      aws_api_gateway_method.options,
      aws_api_gateway_integration.get_lambda,
      aws_api_gateway_integration.options_lambda,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.get_lambda,
    aws_api_gateway_integration.options_lambda,
  ]
}

resource "aws_api_gateway_stage" "api" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = var.stage_name
}

resource "aws_api_gateway_api_key" "cloudfront" {
  name        = "${var.api_name}-cloudfront"
  description = "Allows the CloudFront dashboard distribution to call the RecallRadar API."
  enabled     = true
}

resource "aws_api_gateway_usage_plan" "cloudfront" {
  name        = "${var.api_name}-cloudfront"
  description = "Usage plan for RecallRadar dashboard traffic routed through CloudFront."

  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = aws_api_gateway_stage.api.stage_name
  }

  throttle_settings {
    burst_limit = var.throttle_burst_limit
    rate_limit  = var.throttle_rate_limit
  }
}

resource "aws_api_gateway_usage_plan_key" "cloudfront" {
  key_id        = aws_api_gateway_api_key.cloudfront.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.cloudfront.id
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

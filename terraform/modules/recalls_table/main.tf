resource "aws_dynamodb_table" "recalls" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "PK"
  range_key = "SK"

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "classification"
    type = "S"
  }

  attribute {
    name = "source"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "report_date"
    type = "S"
  }

  global_secondary_index {
    name            = "classification-date-index"
    hash_key        = "classification"
    range_key       = "report_date"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "source-date-index"
    hash_key        = "source"
    range_key       = "report_date"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-date-index"
    hash_key        = "status"
    range_key       = "report_date"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_s3_bucket" "specific_scraper_bucket" {
  bucket = "specific-scraper-production"

  tags = {
    Module = "Storage"
  }
  
  server_side_encryption_configuration {
    rule {
      bucket_key_enabled = false
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_policy" "allow_public_access_to_bucket" {
  bucket = aws_s3_bucket.specific_scraper_bucket.id
  policy = data.aws_iam_policy_document.allow_public_access_to_bucket.json
}

data "aws_iam_policy_document" "allow_public_access_to_bucket" {
  statement {
    sid    = "PublicRead"
    effect = "Allow"
    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.specific_scraper_bucket.arn}/*",
    ]
  }
}
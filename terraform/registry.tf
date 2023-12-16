resource "aws_s3_bucket" "docker_images_navee_driver" {
  bucket = "docker-images-navee-driver"
  acl    = "private"

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

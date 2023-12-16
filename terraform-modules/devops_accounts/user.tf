resource "aws_iam_user" "terraform" {
  name = "terraform"
  path = "/devops/automation/"

  tags = {
    Role = "DevOps"
  }
}

resource "aws_iam_user" "gitlab" {
  name = "gitlab"
  path = "/devops/automation/"

  tags = {
    Role = "DevOps"
  }
}
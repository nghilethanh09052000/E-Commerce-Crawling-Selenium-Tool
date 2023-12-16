resource "aws_iam_user" "specific-scraper-app" {
  name = "specific-scraper-app"

  tags = {
    Role = "DevOps"
  }
}

resource "aws_iam_policy_attachment" "admin_attachment" {
  name = "admin-attachment"
  users = [
    aws_iam_user.specific-scraper-app.name
  ]

  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

  lifecycle {
    ignore_changes = [
      groups,
      users
    ]
  }
}
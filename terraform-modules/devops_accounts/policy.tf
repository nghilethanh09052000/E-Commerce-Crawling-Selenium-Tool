resource "aws_iam_policy_attachment" "admin_attachment" {
  name = "admin-attachment"
  users = [
    aws_iam_user.terraform.name,
    aws_iam_user.gitlab.name
  ]

  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

  lifecycle {
    ignore_changes = [
      groups,
      users
    ]
  }
}
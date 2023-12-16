resource "aws_security_group" "ecs" {
  name   = "ecs"
  vpc_id = local.vpc_id

  ingress = [
    {
      description      = "everything"
      self             = false
      security_groups  = []
      prefix_list_ids  = []
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    }
  ]

  egress = [
    {
      description      = "everything"
      self             = false
      security_groups  = []
      prefix_list_ids  = []
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    }
  ]

  tags = {
    Module = "Security"
    Name   = "ecs"
  }
}
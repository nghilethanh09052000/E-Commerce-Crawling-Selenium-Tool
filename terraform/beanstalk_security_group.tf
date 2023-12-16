resource "aws_security_group" "navee_driver" {
  name   = "navee-driver"
  vpc_id = aws_vpc.main.id

  ingress = [
    {
      description      = "HTTP"
      from_port        = 80
      to_port          = 80
      protocol         = "tcp"
      cidr_blocks      = [aws_subnet.public_main.cidr_block, aws_subnet.public_secondary.cidr_block]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
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
    Name   = "navee-driver"
  }
}

resource "aws_security_group" "worker" {
  name   = "scraping-worker"
  vpc_id = aws_vpc.main.id

  ingress = [
    {
      description      = "only 8000"
      from_port        = 8000
      to_port          = 8000
      protocol         = "tcp"
      cidr_blocks      = [aws_subnet.public_main.cidr_block]
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
    Name   = "worker"
  }
}
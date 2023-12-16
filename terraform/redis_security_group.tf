resource "aws_security_group" "redis" {
  name   = "redis-specific-scraper"
  vpc_id = aws_vpc.main.id

  ingress = [
    {
      description      = "only ecs"
      from_port        = 6379
      to_port          = 6379
      protocol         = "tcp"
      cidr_blocks      = []
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups = [
        aws_security_group.ecs.id,
        aws_security_group.database_bastion_security_group.id,
        aws_security_group.navee_driver.id,
        aws_security_group.worker.id
      ]
      self = false
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
    Name   = "redis"
  }
}

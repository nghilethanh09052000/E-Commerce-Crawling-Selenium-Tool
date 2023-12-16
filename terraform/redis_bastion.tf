resource "aws_instance" "redis_bastion" {
  ami                         = data.aws_ami.ubuntu.id
  key_name                    = aws_key_pair.database_bastion_key.key_name
  vpc_security_group_ids      = [aws_security_group.database_bastion_security_group.id]
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.public_main.id

  tags = {
    Module = "Storage"
    Name   = "redis-bastion"
  }

  lifecycle {
    ignore_changes = [ami] # We don't want to rebuild the instance every time a new version is available
  }
}

resource "aws_eip" "redis_bastion" {
  vpc = true

  instance   = aws_instance.redis_bastion.id
  depends_on = [aws_internet_gateway.main]

  tags = {
    Name = "redis-bastion"
  }
}

output "redis_bastion_public_ip" {
  value = aws_eip.redis_bastion.public_ip
}

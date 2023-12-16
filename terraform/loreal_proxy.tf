resource "aws_instance" "loreal_proxy" {
  ami                         = data.aws_ami.ubuntu.id
  key_name                    = aws_key_pair.loreal_proxy_key.key_name
  vpc_security_group_ids      = [aws_security_group.loreal_proxy_security_group.id]
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.public_main.id

  tags = {
    Module = "Network"
    Name   = "loreal-proxy"
  }

  lifecycle {
    ignore_changes = [ami] # We don't want to rebuild the instance every time a new version is available
  }
}

resource "aws_key_pair" "loreal_proxy_key" {
  key_name   = "antoine.bellami"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMpK7m45X46CkEvmT/RwJ70E2NVoP/GnCAFdQ8JAEe1j Antoine Navee X1"
}

resource "aws_security_group" "loreal_proxy_security_group" {
  name   = "loreal-proxy-security-group"
  vpc_id = aws_vpc.main.id

  ingress {
    description      = "SSH"
    self             = false
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "Proxy connection"
    self             = false
    from_port        = 3128
    to_port          = 3128
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
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

  tags = {
    Module = "Network"
    Name   = "loreal-proxy"
  }
}

resource "aws_eip" "loreal_proxy" {
  vpc = true

  instance   = aws_instance.loreal_proxy.id
  depends_on = [aws_internet_gateway.main]

  tags = {
    Module = "Network"
    Name = "loreal-proxy"
  }
}

output "loreal_proxy_public_ip" {
  value = aws_eip.loreal_proxy.public_ip
}

# To deploy only the proxy instance: terraform apply -var-file="secrets.tfvars" --target aws_eip.loreal_proxy

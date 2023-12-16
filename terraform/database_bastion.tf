data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "database_bastion" {
  ami                         = data.aws_ami.ubuntu.id
  key_name                    = aws_key_pair.database_bastion_key.key_name
  vpc_security_group_ids      = [aws_security_group.database_bastion_security_group.id]
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.public_main.id

  tags = {
    Module = "Storage"
    Name   = "database-bastion"
  }

  lifecycle {
    ignore_changes = [ami] # We don't want to rebuild the instance every time a new version is available
  }
}

resource "aws_key_pair" "database_bastion_key" {
  key_name   = "mathieu"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDQKTDO7+yTh6cp6PHElF8ske3i7d5RNnoRFE20r/VIlLdlHr+O4wd+nTHSKNTYUhcbWTw7yAiZLxBZtiHo631SHSyn0c2csQRzHFF/M2sAcMKJRTxLds4IJX435tk+S+nqq8Ui0zPjCdcdPyUaKLh/xbTuWd5R6OKkYZkKgoliTVxbqlR35H9EZYYtrK53ff//jKlfAqliDtSm/fDk3AvkwImtqMEDLOvk2kgLkWJ5Z7yN6KicuquggF5JgElqH64NbkdUeTXlwyfeD709vUsOZ76wkYuR8D9owsVOHXipoDsrosUpIthcfLZxdjw603fLrJ740rbokAnyACKHmy+v mathieu@mathieu-navee"
}

resource "aws_security_group" "database_bastion_security_group" {
  name   = "database-bastion-security-group"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["0.0.0.0/0"]
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
    Module = "Storage"
    Name   = "database-bastion"
  }
}

resource "aws_eip" "database_bastion" {
  vpc = true

  instance   = aws_instance.database_bastion.id
  depends_on = [aws_internet_gateway.main]

  tags = {
    Module = "Storage"
    Name = "database-bastion"
  }
}

output "database_bastion_public_ip" {
  value = aws_eip.database_bastion.public_ip
}
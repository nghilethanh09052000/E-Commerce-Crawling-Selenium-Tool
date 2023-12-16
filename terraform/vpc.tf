resource "aws_vpc" "main" {
  cidr_block           = "10.1.0.0/16"
  instance_tenancy     = "default"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Module = "Network"
    Name   = "main"
  }
}

resource "aws_subnet" "public_main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.1.0.0/18"
  map_public_ip_on_launch = "true" # if public subnet
  availability_zone       = var.default_az

  tags = {
    Module = "Network"
    Name   = "public-main"
  }
}

resource "aws_subnet" "public_secondary" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.1.64.0/18"
  map_public_ip_on_launch = "true" # if public subnet
  availability_zone       = var.second_az

  tags = {
    Module = "Network"
    Name   = "public-secondary"
  }
}

resource "aws_subnet" "private_main" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.1.128.0/18"
  availability_zone = var.default_az

  tags = {
    Module = "Network"
    Name   = "private-main"
  }
}

resource "aws_subnet" "private_secondary" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.1.192.0/18"
  availability_zone = var.second_az

  tags = {
    Module = "Network"
    Name   = "private-secondary"
  }
}

locals {
    public_subnet_id = aws_subnet.public_main.id
    public_secondary_subnet_id = aws_subnet.public_secondary.id
    private_subnet_id = aws_subnet.private_main.id
    private_secondary_subnet_id = aws_subnet.private_secondary.id
    public_subnet_cidr = aws_subnet.public_main.cidr_block
    vpc_id = aws_vpc.main.id
}

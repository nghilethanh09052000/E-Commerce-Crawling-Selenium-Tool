# Private main
resource "aws_nat_gateway" "private_main" {
  allocation_id = aws_eip.private_main_subnet.id
  subnet_id     = aws_subnet.private_main.id

  tags = {
    Module = "Network"
    Name = "nat_gateway"
  }

  # nat requires an internet gateway
  depends_on = [aws_internet_gateway.main]
}

resource "aws_eip" "private_main_subnet" {
  vpc        = true

  # nat requires an internet gateway
  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private_main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.private_main.id
  }

  lifecycle {
    ignore_changes = [
      route
    ]
  }

  tags = {
    Module = "Network"
    Name = "nat_gateway"
  }
}

# Private secondary
resource "aws_nat_gateway" "private_secondary" {
  allocation_id = aws_eip.private_secondary_subnet.id
  subnet_id     = aws_subnet.private_secondary.id

  tags = {
    Module = "Network"
    Name = "nat_gateway"
  }

  # nat requires an internet gateway
  depends_on = [aws_internet_gateway.main]
}

resource "aws_eip" "private_secondary_subnet" {
  vpc        = true

  # nat requires an internet gateway
  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private_secondary" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.private_secondary.id
  }

  lifecycle {
    ignore_changes = [
      route
    ]
  }

  tags = {
    Module = "Network"
    Name = "nat_gateway"
  }
}

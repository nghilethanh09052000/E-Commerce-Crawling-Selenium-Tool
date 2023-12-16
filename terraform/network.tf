resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Module = "Network"
    Name   = "main"
  }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    //associated subnet can reach everywhere
    cidr_block = "0.0.0.0/0"
    //CRT uses this IGW to reach internet
    gateway_id = aws_internet_gateway.main.id
  }

  lifecycle {
    ignore_changes = [
      route
    ]
  }

  tags = {
    Module = "Network"
    Name   = "main"
  }
}

resource "aws_route_table_association" "public_main" {
  subnet_id      = aws_subnet.public_main.id
  route_table_id = aws_route_table.main.id
}

resource "aws_route_table_association" "public_secondary" {
  subnet_id      = aws_subnet.public_secondary.id
  route_table_id = aws_route_table.main.id
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "redis-specific-scraper"
  subnet_ids = [aws_subnet.public_main.id]

  tags = {
    Module = "Storage"
  }
}

resource "aws_elasticache_replication_group" "main" {
  automatic_failover_enabled    = true
  replication_group_id          = "redis-specific-scraper"
  replication_group_description = "Main redis database"
  node_type                     = "cache.t3.small"
  number_cache_clusters         = "3"
  parameter_group_name          = "default.redis7"
  security_group_ids            = [aws_security_group.redis.id]
  subnet_group_name             = aws_elasticache_subnet_group.main.name
  maintenance_window            = "Mon:15:00-Mon:16:00"

  tags = {
    Module = "Storage"
  }
}

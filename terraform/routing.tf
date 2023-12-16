
resource "aws_route53_zone" "navee_driver_domain" {
  name = var.domain_name
}

resource "aws_route53_record" "navee_driver_domain" {
  zone_id = aws_route53_zone.navee_driver_domain.zone_id
  name    = aws_route53_zone.navee_driver_domain.name
  type    = "A"

  alias {
    name                   = aws_elastic_beanstalk_environment.navee_driver.cname
    zone_id                = data.aws_elastic_beanstalk_hosted_zone.current.id
    evaluate_target_health = true
  }
}

output "aws_route53_backend_zone_id" {
  value = aws_route53_zone.navee_driver_domain.id
}

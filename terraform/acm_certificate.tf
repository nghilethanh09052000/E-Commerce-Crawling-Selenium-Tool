resource "aws_acm_certificate" "navee_driver" {
  domain_name       = var.domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "navee_driver" {
  for_each = {
    for dvo in aws_acm_certificate.navee_driver.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.navee_driver_domain.zone_id
}

resource "aws_acm_certificate_validation" "navee_driver" {
  certificate_arn         = aws_acm_certificate.navee_driver.arn
  validation_record_fqdns = [for record in aws_route53_record.navee_driver : record.fqdn]
}

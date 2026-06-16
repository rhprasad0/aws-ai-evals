locals {
  use_custom_domain = var.custom_domain_name != null && var.route53_zone_name != null
}

data "aws_route53_zone" "frontend" {
  count        = local.use_custom_domain ? 1 : 0
  name         = var.route53_zone_name
  private_zone = false
}

resource "aws_acm_certificate" "frontend" {
  count             = local.use_custom_domain ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = var.custom_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

resource "aws_route53_record" "frontend_certificate_validation" {
  for_each = local.use_custom_domain ? {
    for option in aws_acm_certificate.frontend[0].domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.frontend[0].zone_id
}

resource "aws_acm_certificate_validation" "frontend" {
  count                   = local.use_custom_domain ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for record in aws_route53_record.frontend_certificate_validation : record.fqdn]
}

resource "aws_route53_record" "frontend_a" {
  count   = local.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = var.custom_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "frontend_aaaa" {
  count   = local.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = var.custom_domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

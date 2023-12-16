from typing import List

from marshmallow import fields

from . import CustomSchema


class ProxyCredentialsSchema(CustomSchema):
    host = fields.Str(missing=None)
    port = fields.Int(missing=None)
    port_range = fields.Str(missing=None)
    username = fields.Str(missing=None)
    password = fields.Str(missing=None)


class ProxySchema(CustomSchema):
    name = fields.Str()
    default_country = fields.Str()
    credentials: ProxyCredentialsSchema = fields.Nested(ProxyCredentialsSchema)
    switch_ip_url = fields.Str(missing=None)


class ProxiesSchema(CustomSchema):
    proxies: List[ProxySchema] = fields.List(fields.Nested(ProxySchema), missing=None)

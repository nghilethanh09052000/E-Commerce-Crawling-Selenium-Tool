from marshmallow import Schema, post_load


class CustomSchema(Schema):
    @post_load
    def post_load(self, data, **kwargs):
        return ConfigFile(**data)


class ConfigFile:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)

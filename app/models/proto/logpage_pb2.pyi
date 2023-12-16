from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Logpage(_message.Message):
    __slots__ = ["data_type", "data"]

    class LogDataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        ScrapingResult: _ClassVar[Logpage.LogDataType]
    ScrapingResult: Logpage.LogDataType
    DATA_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    data_type: Logpage.LogDataType
    data: bytes
    def __init__(
        self, data_type: _Optional[_Union[Logpage.LogDataType, str]] = ..., data: _Optional[bytes] = ...
    ) -> None: ...

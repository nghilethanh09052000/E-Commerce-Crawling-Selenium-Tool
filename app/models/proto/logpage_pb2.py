# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: logpage.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor.FileDescriptor(
    name="logpage.proto",
    package="Logpage",
    syntax="proto3",
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n\rlogpage.proto\x12\x07Logpage"k\n\x07Logpage\x12/\n\tdata_type\x18\x01 \x01(\x0e\x32\x1c.Logpage.Logpage.LogDataType\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c"!\n\x0bLogDataType\x12\x12\n\x0eScrapingResult\x10\x00\x62\x06proto3',
)


_LOGPAGE_LOGDATATYPE = _descriptor.EnumDescriptor(
    name="LogDataType",
    full_name="Logpage.Logpage.LogDataType",
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
        _descriptor.EnumValueDescriptor(
            name="ScrapingResult",
            index=0,
            number=0,
            serialized_options=None,
            type=None,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=100,
    serialized_end=133,
)
_sym_db.RegisterEnumDescriptor(_LOGPAGE_LOGDATATYPE)


_LOGPAGE = _descriptor.Descriptor(
    name="Logpage",
    full_name="Logpage.Logpage",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name="data_type",
            full_name="Logpage.Logpage.data_type",
            index=0,
            number=1,
            type=14,
            cpp_type=8,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="data",
            full_name="Logpage.Logpage.data",
            index=1,
            number=2,
            type=12,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"",
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[
        _LOGPAGE_LOGDATATYPE,
    ],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=26,
    serialized_end=133,
)

_LOGPAGE.fields_by_name["data_type"].enum_type = _LOGPAGE_LOGDATATYPE
_LOGPAGE_LOGDATATYPE.containing_type = _LOGPAGE
DESCRIPTOR.message_types_by_name["Logpage"] = _LOGPAGE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Logpage = _reflection.GeneratedProtocolMessageType(
    "Logpage",
    (_message.Message,),
    {
        "DESCRIPTOR": _LOGPAGE,
        "__module__": "logpage_pb2"
        # @@protoc_insertion_point(class_scope:Logpage.Logpage)
    },
)
_sym_db.RegisterMessage(Logpage)


# @@protoc_insertion_point(module_scope)
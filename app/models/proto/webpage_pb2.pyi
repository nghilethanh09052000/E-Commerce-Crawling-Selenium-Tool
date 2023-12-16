from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class Image(_message.Message):
    __slots__ = ["s3_url", "image_url", "sha256sum", "alt_text"]
    S3_URL_FIELD_NUMBER: _ClassVar[int]
    IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    SHA256SUM_FIELD_NUMBER: _ClassVar[int]
    ALT_TEXT_FIELD_NUMBER: _ClassVar[int]
    s3_url: str
    image_url: str
    sha256sum: bytes
    alt_text: str
    def __init__(
        self,
        s3_url: _Optional[str] = ...,
        image_url: _Optional[str] = ...,
        sha256sum: _Optional[bytes] = ...,
        alt_text: _Optional[str] = ...,
    ) -> None: ...

class StructuredPostData(_message.Message):
    __slots__ = ["title", "description", "price", "images", "poster_name", "poster_link", "payload"]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    POSTER_NAME_FIELD_NUMBER: _ClassVar[int]
    POSTER_LINK_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    title: str
    description: str
    price: str
    images: _containers.RepeatedCompositeFieldContainer[Image]
    poster_name: str
    poster_link: str
    payload: _struct_pb2.Struct
    def __init__(
        self,
        title: _Optional[str] = ...,
        description: _Optional[str] = ...,
        price: _Optional[str] = ...,
        images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ...,
        poster_name: _Optional[str] = ...,
        poster_link: _Optional[str] = ...,
        payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
    ) -> None: ...

class StructuredPosterData(_message.Message):
    __slots__ = ["name", "description", "translated_description", "profile_pic_url", "payload"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TRANSLATED_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PROFILE_PIC_URL_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    translated_description: str
    profile_pic_url: Image
    payload: _struct_pb2.Struct
    def __init__(
        self,
        name: _Optional[str] = ...,
        description: _Optional[str] = ...,
        translated_description: _Optional[str] = ...,
        profile_pic_url: _Optional[_Union[Image, _Mapping]] = ...,
        payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
    ) -> None: ...

class LinkContext(_message.Message):
    __slots__ = ["images", "adjacent_images", "link_text", "adjacent_text", "payload"]
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    ADJACENT_IMAGES_FIELD_NUMBER: _ClassVar[int]
    LINK_TEXT_FIELD_NUMBER: _ClassVar[int]
    ADJACENT_TEXT_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[Image]
    adjacent_images: _containers.RepeatedCompositeFieldContainer[Image]
    link_text: str
    adjacent_text: str
    payload: _struct_pb2.Struct
    def __init__(
        self,
        images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ...,
        adjacent_images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ...,
        link_text: _Optional[str] = ...,
        adjacent_text: _Optional[str] = ...,
        payload: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
    ) -> None: ...

class IncomingLink(_message.Message):
    __slots__ = ["from_url", "context", "from_title"]
    FROM_URL_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    FROM_TITLE_FIELD_NUMBER: _ClassVar[int]
    from_url: str
    context: LinkContext
    from_title: str
    def __init__(
        self,
        from_url: _Optional[str] = ...,
        context: _Optional[_Union[LinkContext, _Mapping]] = ...,
        from_title: _Optional[str] = ...,
    ) -> None: ...

class OutgoingLink(_message.Message):
    __slots__ = ["to_url", "context"]
    TO_URL_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    to_url: str
    context: LinkContext
    def __init__(
        self, to_url: _Optional[str] = ..., context: _Optional[_Union[LinkContext, _Mapping]] = ...
    ) -> None: ...

class Webpage(_message.Message):
    __slots__ = [
        "url",
        "s3_content_url",
        "s3_archive_url",
        "incoming_links",
        "outgoing_links",
        "images",
        "title",
        "translated_title",
        "description",
        "translated_description",
        "source_language",
        "creation_date_timestamp",
        "main_post_id",
        "main_poster_id",
        "post",
        "poster",
    ]
    URL_FIELD_NUMBER: _ClassVar[int]
    S3_CONTENT_URL_FIELD_NUMBER: _ClassVar[int]
    S3_ARCHIVE_URL_FIELD_NUMBER: _ClassVar[int]
    INCOMING_LINKS_FIELD_NUMBER: _ClassVar[int]
    OUTGOING_LINKS_FIELD_NUMBER: _ClassVar[int]
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    TRANSLATED_TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TRANSLATED_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CREATION_DATE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    MAIN_POST_ID_FIELD_NUMBER: _ClassVar[int]
    MAIN_POSTER_ID_FIELD_NUMBER: _ClassVar[int]
    POST_FIELD_NUMBER: _ClassVar[int]
    POSTER_FIELD_NUMBER: _ClassVar[int]
    url: str
    s3_content_url: str
    s3_archive_url: str
    incoming_links: _containers.RepeatedCompositeFieldContainer[IncomingLink]
    outgoing_links: _containers.RepeatedCompositeFieldContainer[OutgoingLink]
    images: _containers.RepeatedCompositeFieldContainer[Image]
    title: str
    translated_title: str
    description: str
    translated_description: str
    source_language: str
    creation_date_timestamp: str
    main_post_id: str
    main_poster_id: str
    post: _containers.RepeatedCompositeFieldContainer[StructuredPostData]
    poster: _containers.RepeatedCompositeFieldContainer[StructuredPosterData]
    def __init__(
        self,
        url: _Optional[str] = ...,
        s3_content_url: _Optional[str] = ...,
        s3_archive_url: _Optional[str] = ...,
        incoming_links: _Optional[_Iterable[_Union[IncomingLink, _Mapping]]] = ...,
        outgoing_links: _Optional[_Iterable[_Union[OutgoingLink, _Mapping]]] = ...,
        images: _Optional[_Iterable[_Union[Image, _Mapping]]] = ...,
        title: _Optional[str] = ...,
        translated_title: _Optional[str] = ...,
        description: _Optional[str] = ...,
        translated_description: _Optional[str] = ...,
        source_language: _Optional[str] = ...,
        creation_date_timestamp: _Optional[str] = ...,
        main_post_id: _Optional[str] = ...,
        main_poster_id: _Optional[str] = ...,
        post: _Optional[_Iterable[_Union[StructuredPostData, _Mapping]]] = ...,
        poster: _Optional[_Iterable[_Union[StructuredPosterData, _Mapping]]] = ...,
    ) -> None: ...

class Webhost(_message.Message):
    __slots__ = ["fqdn", "port"]
    FQDN_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    fqdn: str
    port: int
    def __init__(self, fqdn: _Optional[str] = ..., port: _Optional[int] = ...) -> None: ...

class WebhostInfo(_message.Message):
    __slots__ = ["webshot", "who_is", "web_stack"]
    WEBSHOT_FIELD_NUMBER: _ClassVar[int]
    WHO_IS_FIELD_NUMBER: _ClassVar[int]
    WEB_STACK_FIELD_NUMBER: _ClassVar[int]
    webshot: Webhost
    who_is: _struct_pb2.Struct
    web_stack: _struct_pb2.Struct
    def __init__(
        self,
        webshot: _Optional[_Union[Webhost, _Mapping]] = ...,
        who_is: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        web_stack: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
    ) -> None: ...

class ScrapingResult(_message.Message):
    __slots__ = ["pages", "hosts", "errors", "successful"]
    PAGES_FIELD_NUMBER: _ClassVar[int]
    HOSTS_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_FIELD_NUMBER: _ClassVar[int]
    pages: _containers.RepeatedCompositeFieldContainer[Webpage]
    hosts: _containers.RepeatedCompositeFieldContainer[WebhostInfo]
    errors: _containers.RepeatedScalarFieldContainer[str]
    successful: bool
    def __init__(
        self,
        pages: _Optional[_Iterable[_Union[Webpage, _Mapping]]] = ...,
        hosts: _Optional[_Iterable[_Union[WebhostInfo, _Mapping]]] = ...,
        errors: _Optional[_Iterable[str]] = ...,
        successful: bool = ...,
    ) -> None: ...

from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RobotRequest(_message.Message):
    __slots__ = ["asr", "image", "params", "speech", "type"]
    class ParamsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: str
        def __init__(self, key: Optional[str] = ..., value: Optional[str] = ...) -> None: ...
    ASR_FIELD_NUMBER: ClassVar[int]
    IMAGE_FIELD_NUMBER: ClassVar[int]
    PARAMS_FIELD_NUMBER: ClassVar[int]
    SPEECH_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    asr: _containers.RepeatedScalarFieldContainer[int]
    image: bytes
    params: _containers.ScalarMap[str, str]
    speech: str
    type: str
    def __init__(self, type: Optional[str] = ..., asr: Optional[Iterable[int]] = ..., image: Optional[bytes] = ..., params: Optional[Mapping[str, str]] = ..., speech: Optional[str] = ...) -> None: ...

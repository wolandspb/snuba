# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: time_series.proto
# Protobuf Python Version: 5.27.3
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 5, 27, 3, "", "time_series.proto"
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from .base_messages_pb2 import *

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x11time_series.proto\x1a\x13\x62\x61se_messages.proto"\x93\x01\n\x11TimeSeriesRequest\x12"\n\x0crequest_info\x18\x01 \x01(\x0b\x32\x0c.RequestInfo\x12(\n\x0fpentity_filters\x18\x02 \x01(\x0b\x32\x0f.PentityFilters\x12\x30\n\x13pentity_aggregation\x18\x03 \x01(\x0b\x32\x13.PentityAggregationb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "time_series_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals["_TIMESERIESREQUEST"]._serialized_start = 43
    _globals["_TIMESERIESREQUEST"]._serialized_end = 190
# @@protoc_insertion_point(module_scope)

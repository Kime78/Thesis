# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: chunk.proto
# Protobuf Python Version: 6.30.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    30,
    0,
    '',
    'chunk.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0b\x63hunk.proto\x12\x03\x64\x66s\"!\n\x05\x43hunk\x12\n\n\x02id\x18\x01 \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\"1\n\rStoreResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"\"\n\x0c\x43hunkRequest\x12\x12\n\nchunk_uuid\x18\x01 \x01(\t\".\n\rChunkResponse\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x0c\x12\x0f\n\x07success\x18\x02 \x01(\x08\"2\n\x0e\x44\x65leteResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t2\xe0\x01\n\x0c\x43hunkService\x12.\n\nStoreChunk\x12\n.dfs.Chunk\x1a\x12.dfs.StoreResponse\"\x00\x12\x36\n\x10StoreChunkStream\x12\n.dfs.Chunk\x1a\x12.dfs.StoreResponse\"\x00(\x01\x12\x31\n\x08GetChunk\x12\x11.dfs.ChunkRequest\x1a\x12.dfs.ChunkResponse\x12\x35\n\x0b\x44\x65leteChunk\x12\x11.dfs.ChunkRequest\x1a\x13.dfs.DeleteResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'chunk_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_CHUNK']._serialized_start=20
  _globals['_CHUNK']._serialized_end=53
  _globals['_STORERESPONSE']._serialized_start=55
  _globals['_STORERESPONSE']._serialized_end=104
  _globals['_CHUNKREQUEST']._serialized_start=106
  _globals['_CHUNKREQUEST']._serialized_end=140
  _globals['_CHUNKRESPONSE']._serialized_start=142
  _globals['_CHUNKRESPONSE']._serialized_end=188
  _globals['_DELETERESPONSE']._serialized_start=190
  _globals['_DELETERESPONSE']._serialized_end=240
  _globals['_CHUNKSERVICE']._serialized_start=243
  _globals['_CHUNKSERVICE']._serialized_end=467
# @@protoc_insertion_point(module_scope)

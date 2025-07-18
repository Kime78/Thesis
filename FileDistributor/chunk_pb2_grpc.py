# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import chunk_pb2 as chunk__pb2

GRPC_GENERATED_VERSION = '1.72.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in chunk_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class ChunkServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.StoreChunk = channel.unary_unary(
                '/dfs.ChunkService/StoreChunk',
                request_serializer=chunk__pb2.Chunk.SerializeToString,
                response_deserializer=chunk__pb2.StoreResponse.FromString,
                _registered_method=True)
        self.StoreChunkStream = channel.stream_unary(
                '/dfs.ChunkService/StoreChunkStream',
                request_serializer=chunk__pb2.Chunk.SerializeToString,
                response_deserializer=chunk__pb2.StoreResponse.FromString,
                _registered_method=True)
        self.GetChunk = channel.unary_unary(
                '/dfs.ChunkService/GetChunk',
                request_serializer=chunk__pb2.ChunkRequest.SerializeToString,
                response_deserializer=chunk__pb2.ChunkResponse.FromString,
                _registered_method=True)


class ChunkServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def StoreChunk(self, request, context):
        """Unary RPC for single chunk
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StoreChunkStream(self, request_iterator, context):
        """Client-side streaming for batches
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetChunk(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ChunkServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'StoreChunk': grpc.unary_unary_rpc_method_handler(
                    servicer.StoreChunk,
                    request_deserializer=chunk__pb2.Chunk.FromString,
                    response_serializer=chunk__pb2.StoreResponse.SerializeToString,
            ),
            'StoreChunkStream': grpc.stream_unary_rpc_method_handler(
                    servicer.StoreChunkStream,
                    request_deserializer=chunk__pb2.Chunk.FromString,
                    response_serializer=chunk__pb2.StoreResponse.SerializeToString,
            ),
            'GetChunk': grpc.unary_unary_rpc_method_handler(
                    servicer.GetChunk,
                    request_deserializer=chunk__pb2.ChunkRequest.FromString,
                    response_serializer=chunk__pb2.ChunkResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'dfs.ChunkService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('dfs.ChunkService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class ChunkService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def StoreChunk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dfs.ChunkService/StoreChunk',
            chunk__pb2.Chunk.SerializeToString,
            chunk__pb2.StoreResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def StoreChunkStream(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_unary(
            request_iterator,
            target,
            '/dfs.ChunkService/StoreChunkStream',
            chunk__pb2.Chunk.SerializeToString,
            chunk__pb2.StoreResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetChunk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dfs.ChunkService/GetChunk',
            chunk__pb2.ChunkRequest.SerializeToString,
            chunk__pb2.ChunkResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

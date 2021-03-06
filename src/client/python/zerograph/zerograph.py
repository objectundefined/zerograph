#!/usr/bin/env python

from inspect import isgeneratorfunction
import json
import logging

import zmq

from .data import Data
from .entities import *


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def hydrate(string):
    # TODO: expand attributes to kwargs for cleaner constructors
    data = Data.decode(string)
    if data.class_name == "Zerograph":
        return Zerograph(data.value)
    elif data.class_name == "Graph":
        return Graph(data.value)
    elif data.class_name == "Node":
        return Node(data.value)
    elif data.class_name == "Rel":
        return Rel(data.value)
    elif data.class_name == "Pointer":
        return Pointer(data.value)
    else:
        return data.value


def dehydrate(obj):
    if isinstance(obj, Pointer):
        return Data("Pointer", obj.address).encode()
    else:
        return json.dumps(obj, separators=",:")


class ClientError(Exception):
    pass


class BadRequest(ClientError):
    pass


class NotFound(ClientError):
    pass


class MethodNotAllowed(ClientError):
    pass


class Conflict(ClientError):
    pass


class ServerError(Exception):
    pass


ERRORS = {
    400: BadRequest,
    404: NotFound,
    405: MethodNotAllowed,
    409: Conflict,
    500: ServerError,
}


class Request(object):

    def __init__(self, method, resource, *data):
        self.__method = method
        self.__resource = resource
        self.__data = data

    @property
    def method(self):
        return self.__method

    @property
    def resource(self):
        return self.__resource

    @property
    def data(self):
        return self.__data

    def send(self, socket, more=False):
        args = [self.__method, self.__resource]
        args.extend(map(dehydrate, self.__data))
        line = "\t".join(args)
        socket.send(line.encode("utf-8"), zmq.SNDMORE if more else 0)


class Response(object):

    @classmethod
    def receive(cls, socket):
        status = 0
        while status < 200:
            try:
                frame = socket.recv().decode("utf-8")
            except zmq.error.ZMQError as err:
                raise TimeoutError("Timeout occurred while trying to receive "
                                   "data")
            for line in frame.splitlines(keepends=False):
                if line:
                    parts = line.split("\t")
                    status = int(parts[0])
                    data = tuple(hydrate(part) for part in parts[1:])
                    if status >= 400:
                        raise ERRORS[status](*data)
                    yield cls(status, *data)

    @classmethod
    def single(cls, socket):
        rs = list(cls.receive(socket))
        if len(rs) != 1:
            raise TypeError("Expected single line response")
        rs = rs[0]
        value_count = len(rs.data)
        if value_count == 0:
            return None
        elif value_count == 1:
            return rs.data[0]
        else:
            raise TypeError("Expected single value response")

    @classmethod
    def tabular(cls, socket):
        return Table(cls.receive(socket))

    def __init__(self, status, *data):
        self.__status = status
        self.__data = data

    def __repr__(self):
        return "<Response status={0} data={1}>".format(self.__status, self.__data)

    @property
    def status(self):
        return self.__status

    @property
    def data(self):
        return self.__data


class Table(object):

    def __init__(self, responses):
        self.__columns = next(responses).data
        self.__rows = []
        self.__stats = None
        for rs in responses:
            if rs.status < 200:
                self.__rows.append(rs.data)
            else:
                self.__stats = rs.data

    def __repr__(self):
        column_widths = [len(column) for column in self.__columns]
        for row in self.__rows:
            for i, value in enumerate(row):
                column_widths[i] = max(column_widths[i], len(repr(value)))
        out = [" " + " | ".join(column.ljust(column_widths[i])
                                for i, column in enumerate(self.__columns)) + " "]
        out += ["-" + "-+-".join("-" * column_widths[i]
                                 for i, column in enumerate(self.__columns)) + "-"]
        for row in self.__rows:
            out.append(" " + " | ".join(repr(value).ljust(column_widths[i])
                                        for i, value in enumerate(row)) + " ")
        return "\n".join(out)
        #return "<Table columns={0} row_count={1}>".format(self.__columns, len(self.__rows))

    @property
    def columns(self):
        return self.__columns

    @property
    def rows(self):
        return self.__rows

    @property
    def stats(self):
        return self.__stats


class _Batch(object):

    @classmethod
    def single(cls, socket, method, *args, **kwargs):
        batch = cls(socket)
        method(batch, *args, **kwargs)
        rs = list(batch.submit())
        return rs[0]

    def __init__(self, socket):
        self.__socket = socket
        self.__response_handlers = []

    def prepare(self, response_handler, method, resource, *args):
        Request(method, resource, *args).send(self.__socket, more=True)
        pointer = Pointer(len(self.__response_handlers))
        self.__response_handlers.append(response_handler)
        return pointer

    def submit(self):
        self.__socket.send(b"")  # to close multipart message
        for handler in self.__response_handlers:
            if isgeneratorfunction(handler):
                yield list(handler(self.__socket))
            else:
                yield handler(self.__socket)
        next(Response.receive(self.__socket))  # overall batch response


class ZerographBatch(_Batch):

    def get_graph(self, host, port):
        return self.prepare(Response.single, "GET", "graph", host, int(port))

    def open_graph(self, host, port, create=False):
        return self.prepare(Response.single, "PUT", "graph", host, int(port), create)

    def close_graph(self, host, port, delete=False):
        return self.prepare(Response.single, "DELETE", "graph", host, int(port), delete)


class GraphBatch(_Batch):

    def execute(self, query):
        return self.prepare(Response.tabular, "POST", "cypher", query)

    def get_node(self, node_id):
        return self.prepare(Response.single, "GET", "node", int(node_id))

    def put_node(self, node_id, labels, properties):
        return self.prepare(Response.single, "PUT", "node", int(node_id), labels, properties)

    def patch_node(self, node_id, labels, properties):
        return self.prepare(Response.single, "PATCH", "node", int(node_id), labels, properties)

    def create_node(self, labels, properties):
        return self.prepare(Response.single, "POST", "node", labels, properties)

    def delete_node(self, node_id):
        return self.prepare(Response.single, "DELETE", "node", int(node_id))

    def get_rel(self, rel_id):
        return self.prepare(Response.single, "GET", "rel", int(rel_id))

    def put_rel(self, rel_id, properties):
        return self.prepare(Response.single, "PUT", "rel", int(rel_id), properties)

    def patch_rel(self, rel_id, properties):
        return self.prepare(Response.single, "PATCH", "rel", int(rel_id), properties)

    def create_rel(self, start_node, end_node, type, properties):
        return self.prepare(Response.single, "POST", "rel", start_node, end_node, type, properties)

    def delete_rel(self, rel_id):
        return self.prepare(Response.single, "DELETE", "rel", int(rel_id))


class _Client(object):

    def __init__(self, attributes):
        zerograph = attributes.get("zerograph")
        if zerograph:
            self.__zerograph = Zerograph(zerograph)
        else:
            self.__zerograph = None
        self.__host = attributes["host"]
        self.__port = attributes["port"]
        self.__address = "tcp://{0}:{1}".format(self.__host, self.__port)
        self.__context = zmq.Context()
        self.__socket = self.__context.socket(zmq.REQ)
        self.__socket.setsockopt(zmq.RCVTIMEO, 30000)  # TODO: configurable timeout
        try:
            self.__socket.connect(self.__address)
        except zmq.error.ZMQError as err:
            raise TimeoutError("Timeout occurred while trying to connect to "
                               "{0} on port {1}".format(self.__host,
                                                        self.__port))

    @property
    def zerograph(self):
        return self.__zerograph

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def socket(self):
        return self.__socket


class Zerograph(_Client):

    def __init__(self, attributes=None, host=None, port=None):
        # TODO: maybe sniff types of arguments?
        attributes = dict(attributes or {})
        if host:
            attributes["host"] = host
        else:
            attributes.setdefault("host", "localhost")
        if port:
            attributes["port"] = port
        else:
            attributes.setdefault("port", 47470)
        _Client.__init__(self, attributes)

    @property
    def zerograph(self):
        return self

    def get_graph(self, port):
        return ZerographBatch.single(self.socket, ZerographBatch.get_graph, self.host, port)

    def open_graph(self, port, create=False):
        return ZerographBatch.single(self.socket, ZerographBatch.open_graph, self.host, port, create)

    def close_graph(self, port, delete=False):
        return ZerographBatch.single(self.socket, ZerographBatch.close_graph, self.host, port, delete)


class Graph(_Client):

    def __init__(self, attributes):
        _Client.__init__(self, attributes)

    def close(self, delete=False):
        self.zerograph.close_graph(self.port, delete=delete)

    def create_batch(self):
        return GraphBatch(self.__socket)

    def execute(self, query):
        return GraphBatch.single(self.socket, GraphBatch.execute, query)

    def get_node(self, node_id):
        return GraphBatch.single(self.socket, GraphBatch.get_node, node_id)

    def put_node(self, node_id, labels, properties):
        return GraphBatch.single(self.socket, GraphBatch.put_node, node_id, labels, properties)

    def patch_node(self, node_id, labels, properties):
        return GraphBatch.single(self.socket, GraphBatch.patch_node, node_id, labels, properties)

    def create_node(self, labels, properties):
        return GraphBatch.single(self.socket, GraphBatch.create_node, labels, properties)

    def delete_node(self, node_id):
        return GraphBatch.single(self.socket, GraphBatch.delete_node, node_id)

    def get_rel(self, rel_id):
        return GraphBatch.single(self.socket, GraphBatch.get_rel, rel_id)

    def put_rel(self, rel_id, properties):
        return GraphBatch.single(self.socket, GraphBatch.put_rel, rel_id, properties)

    def patch_rel(self, rel_id, properties):
        return GraphBatch.single(self.socket, GraphBatch.patch_rel, rel_id, properties)

    def create_rel(self, start_node, end_node, type, properties):
        return GraphBatch.single(self.socket, GraphBatch.create_rel, start_node, end_node, type, properties)

    def delete_rel(self, rel_id):
        return GraphBatch.single(self.socket, GraphBatch.delete_rel, rel_id)

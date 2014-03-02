package com.nigelsmall.zerograph.resources;

import com.nigelsmall.zerograph.Request;
import com.nigelsmall.zerograph.Response;
import com.nigelsmall.zerograph.except.ClientError;
import com.nigelsmall.zerograph.except.ServerError;
import org.neo4j.cypher.CypherException;
import org.neo4j.cypher.javacompat.ExecutionEngine;
import org.neo4j.cypher.javacompat.ExecutionResult;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.PropertyContainer;
import org.neo4j.graphdb.Transaction;
import org.zeromq.ZMQ;

import java.io.IOException;
import java.util.List;
import java.util.Map;

public abstract class Resource {

    final public static String NAME = null;

    final private GraphDatabaseService database;
    final private ExecutionEngine engine;
    final private ZMQ.Socket socket;

    public Resource(GraphDatabaseService database, ZMQ.Socket socket) {
        this.database = database;
        this.engine = new ExecutionEngine(database);
        this.socket = socket;
    }

    public GraphDatabaseService database() {
        return this.database;
    }

    public ExecutionResult execute(String query) throws CypherException {
        return this.engine.execute(query);
    }

    public ExecutionResult execute(String query, Map<String, Object> params) throws CypherException {
        return this.engine.execute(query, params);
    }

    public ExecutionResult profile(String query, Map<String, Object> params) throws CypherException {
        return this.engine.profile(query, params);
    }

    public PropertyContainer handle(Transaction tx, Request request) throws ClientError, ServerError {
        switch (request.getMethod()) {
            case "GET":
                return get(tx, request);
            case "PUT":
                return put(tx, request);
            case "PATCH":
                return patch(tx, request);
            case "POST":
                return post(tx, request);
            case "DELETE":
                return delete(tx, request);
            default:
                throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
        }
    }

    public PropertyContainer get(Transaction tx, Request request) throws ClientError, ServerError {
        throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
    }

    public PropertyContainer put(Transaction tx, Request request) throws ClientError, ServerError {
        throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
    }

    public PropertyContainer patch(Transaction tx, Request request) throws ClientError, ServerError {
        throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
    }

    public PropertyContainer post(Transaction tx, Request request) throws ClientError, ServerError {
        throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
    }

    public PropertyContainer delete(Transaction tx, Request request) throws ClientError, ServerError {
        throw new ClientError(new Response(Response.METHOD_NOT_ALLOWED, request.getMethod()));
    }

    private void send(Response response) {
        response.send(socket, ZMQ.SNDMORE);
    }

    public void sendContinue(Object... data) {
        send(new Response(Response.CONTINUE, data));
    }

    public void sendOK(Object... data) {
        send(new Response(Response.OK, data));
    }

}

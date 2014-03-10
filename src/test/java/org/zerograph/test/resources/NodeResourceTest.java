package org.zerograph.test.resources;

import org.junit.Before;
import org.junit.Test;
import org.neo4j.graphdb.*;
import org.zerograph.Request;
import org.zerograph.response.status4xx.Abstract4xx;
import org.zerograph.response.status5xx.Abstract5xx;
import org.zerograph.resource.NodeResource;

import java.util.Arrays;
import java.util.HashMap;

public class NodeResourceTest extends ResourceTest {

    protected NodeResource resource;

    @Before
    public void createResource() {
        resource = new NodeResource(server, database);
    }

    protected Node createAlice() {
        Node created = database.createNode();
        resource.addLabels(created, Arrays.asList("Person"));
        HashMap<String, Object> properties = new HashMap<>();
        properties.put("name", "Alice");
        resource.addProperties(created, properties);
        return created;
    }

    protected void assertAlice(Node node) {
        assert node.hasLabel(DynamicLabel.label("Person"));
        assert node.hasProperty("name");
        assert node.getProperty("name").equals("Alice");
    }

    @Test
    public void testCanGetExistingNode() throws Abstract4xx, Abstract5xx {
        String rq = "GET\tnode\t0";
        String rs = "200\t/*Node*/{\"id\":0,\"labels\":[\"Person\"],\"properties\":{\"name\":\"Alice\"}}";
        try (Transaction tx = database.beginTx()) {
            Node created = createAlice();
            assert created.getId() == 0;
            PropertyContainer got = resource.get(new Request(rq), tx);
            assert got instanceof Node;
            assertAlice((Node)got);
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCannotGetNonExistentNode() throws Abstract4xx, Abstract5xx {
        String rq = "GET\tnode\t0";
        String rs = "";
        try (Transaction tx = database.beginTx()) {
            try {
                resource.get(new Request(rq), tx);
                assert false;
            } catch (Abstract4xx err) {
                assert true;
            }
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCanPutExistingNode() throws Abstract4xx, Abstract5xx {
        String rq = "PUT\tnode\t0\t[\"Person\"]\t{\"name\":\"Alice\"}";
        String rs = "200\t/*Node*/{\"id\":0,\"labels\":[\"Person\"],\"properties\":{\"name\":\"Alice\"}}";
        try (Transaction tx = database.beginTx()) {
            Node created = database.createNode();
            assert created.getId() == 0;
            PropertyContainer got = resource.put(new Request(rq), tx);
            assert got instanceof Node;
            assertAlice((Node)got);
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCannotPutNonExistentNode() throws Abstract4xx, Abstract5xx {
        String rq = "PUT\tnode\t0\t[\"Person\"]\t{\"name\":\"Alice\"}";
        String rs = "";
        try (Transaction tx = database.beginTx()) {
            try {
                resource.put(new Request(rq), tx);
                assert false;
            } catch (Abstract4xx err) {
                assert true;
            }
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCanPatchExistingNode() throws Abstract4xx, Abstract5xx {
        String rq = "PATCH\tnode\t0\t[\"Female\"]\t{\"age\":33}";
        String rs = "200\t/*Node*/{\"id\":0,\"labels\":[\"Person\",\"Female\"],\"properties\":{\"name\":\"Alice\",\"age\":33}}";
        try (Transaction tx = database.beginTx()) {
            Node created = createAlice();
            assert created.getId() == 0;
            PropertyContainer got = resource.patch(new Request(rq), tx);
            assert got instanceof Node;
            Node gotNode = (Node)got;
            assertAlice(gotNode);
            assert gotNode.hasLabel(DynamicLabel.label("Female"));
            assert gotNode.hasProperty("age");
            assert gotNode.getProperty("age").equals(33);
        }
        sendClose();
        assert client.recvStr().startsWith("200");
    }

    @Test
    public void testCannotPatchNonExistentNode() throws Abstract4xx, Abstract5xx {
        String rq = "PATCH\tnode\t0\t[\"Female\"]\t{\"age\":33}";
        String rs = "";
        try (Transaction tx = database.beginTx()) {
            try {
                resource.put(new Request(rq), tx);
                assert false;
            } catch (Abstract4xx err) {
                assert true;
            }
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCanCreateNode() throws Abstract4xx, Abstract5xx {
        String rq = "POST\tnode\t[\"Person\"]\t{\"name\":\"Alice\"}";
        String rs = "201\t/*Node*/{\"id\":0,\"labels\":[\"Person\"],\"properties\":{\"name\":\"Alice\"}}";
        try (Transaction tx = database.beginTx()) {
            PropertyContainer created = resource.post(new Request(rq), tx);
            assert created instanceof Node;
            Node node = (Node)created;
            assert node.hasLabel(DynamicLabel.label("Person"));
            assert node.hasProperty("name");
            assert node.getProperty("name").equals("Alice");
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

    @Test
    public void testCanDeleteNode() throws Abstract4xx, Abstract5xx {
        String rq = "DELETE\tnode\t0";
        String rs = "204";
        try (Transaction tx = database.beginTx()) {
            Node created = database.createNode();
            assert created.getId() == 0;
            resource.delete(new Request(rq), tx);
        }
        try (Transaction tx = database.beginTx()) {
            try {
                database.getNodeById(0);
                assert false;
            } catch (NotFoundException ex) {
                assert true;
            }
        }
        sendClose();
        assert client.recvStr().equals(rs);
    }

}

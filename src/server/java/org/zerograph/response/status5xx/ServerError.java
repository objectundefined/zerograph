package org.zerograph.response.status5xx;

public class ServerError extends Abstract5xx {

    public ServerError(Object... data) {
        super(data);
    }

    @Override
    public int getStatus() {
        return SERVER_ERROR;
    }

}

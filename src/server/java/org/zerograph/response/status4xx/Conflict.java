package org.zerograph.response.status4xx;

public class Conflict extends Status4xx {

    public Conflict(Object... data) {
        super(data);
    }

    @Override
    public int getStatus() {
        return CONFLICT;
    }

}

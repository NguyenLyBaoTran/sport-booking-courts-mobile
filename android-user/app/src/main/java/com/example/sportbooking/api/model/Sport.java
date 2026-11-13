package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class Sport {

    private int id;
    private String name;
    private String description;

    @SerializedName("is_active")
    private boolean active;

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public boolean isActive() {
        return active;
    }
}
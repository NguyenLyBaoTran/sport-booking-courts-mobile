package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class Venue {

    private int id;
    private String name;
    private String address;
    private String description;
    private String phone;

    @SerializedName("is_active")
    private boolean active;

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getAddress() {
        return address;
    }

    public String getDescription() {
        return description;
    }

    public String getPhone() {
        return phone;
    }

    public boolean isActive() {
        return active;
    }
}
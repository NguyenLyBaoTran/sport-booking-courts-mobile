package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class Court {

    private int id;
    private String name;
    private String description;

    @SerializedName("venue_id")
    private int venueId;

    @SerializedName("sport_id")
    private int sportId;

    @SerializedName("price_per_hour")
    private String pricePerHour;

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

    public int getVenueId() {
        return venueId;
    }

    public int getSportId() {
        return sportId;
    }

    public String getPricePerHour() {
        return pricePerHour;
    }

    public boolean isActive() {
        return active;
    }
}
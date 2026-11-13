package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class TimeSlot {

    private int id;

    @SerializedName("court_id")
    private int courtId;

    @SerializedName("slot_date")
    private String slotDate;

    @SerializedName("start_time")
    private String startTime;

    @SerializedName("end_time")
    private String endTime;

    private String status;

    @SerializedName("is_active")
    private boolean active;

    public int getId() {
        return id;
    }

    public int getCourtId() {
        return courtId;
    }

    public String getSlotDate() {
        return slotDate;
    }

    public String getStartTime() {
        return startTime;
    }

    public String getEndTime() {
        return endTime;
    }

    public String getStatus() {
        return status;
    }

    public boolean isActive() {
        return active;
    }
}
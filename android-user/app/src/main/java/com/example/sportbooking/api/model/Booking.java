package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class Booking {

    private int id;

    @SerializedName("user_id")
    private int userId;

    @SerializedName("time_slot_id")
    private int timeSlotId;

    private String status;

    @SerializedName("total_amount")
    private String totalAmount;

    @SerializedName("created_at")
    private String createdAt;

    @SerializedName("qr_token")
    private String qrToken;

    public int getId() {
        return id;
    }

    public int getUserId() {
        return userId;
    }

    public int getTimeSlotId() {
        return timeSlotId;
    }

    public String getStatus() {
        return status;
    }

    public String getTotalAmount() {
        return totalAmount;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public String getQrToken() {
        return qrToken;
    }
}
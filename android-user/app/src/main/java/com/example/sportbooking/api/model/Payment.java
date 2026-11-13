package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class Payment {

    private int id;

    @SerializedName("booking_id")
    private int bookingId;

    private String status;

    @SerializedName("transaction_code")
    private String transactionCode;

    @SerializedName("created_at")
    private String createdAt;

    @SerializedName("qr_token")
    private String qrToken;

    public int getId() {
        return id;
    }

    public int getBookingId() {
        return bookingId;
    }

    public String getStatus() {
        return status;
    }

    public String getTransactionCode() {
        return transactionCode;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public String getQrToken() {
        return qrToken;
    }
}
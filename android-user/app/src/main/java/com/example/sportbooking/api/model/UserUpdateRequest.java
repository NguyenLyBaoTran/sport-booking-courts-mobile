package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class UserUpdateRequest {
    @SerializedName("full_name")
    private final String fullName;

    @SerializedName("phone")
    private final String phone;

    public UserUpdateRequest(String fullName, String phone) {
        this.fullName = fullName;
        this.phone = phone;
    }

    public String getFullName() {
        return fullName;
    }

    public String getPhone() {
        return phone;
    }
}

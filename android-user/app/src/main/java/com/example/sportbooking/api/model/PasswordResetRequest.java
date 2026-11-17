package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class PasswordResetRequest {
    @SerializedName("email")
    private final String email;

    @SerializedName("otp_code")
    private final String otpCode;

    @SerializedName("new_password")
    private final String newPassword;

    public PasswordResetRequest(String email, String otpCode, String newPassword) {
        this.email = email;
        this.otpCode = otpCode;
        this.newPassword = newPassword;
    }

    public String getEmail() {
        return email;
    }

    public String getOtpCode() {
        return otpCode;
    }

    public String getNewPassword() {
        return newPassword;
    }
}

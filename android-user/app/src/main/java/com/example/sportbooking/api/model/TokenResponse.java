package com.example.sportbooking.api.model;

public class TokenResponse {

    private String access_token;
    private String token_type;
    private int expires_in;
    private UserResponse user;

    public String getAccess_token() {
        return access_token;
    }

    public String getToken_type() {
        return token_type;
    }

    public int getExpires_in() {
        return expires_in;
    }

    public UserResponse getUser() {
        return user;
    }
}
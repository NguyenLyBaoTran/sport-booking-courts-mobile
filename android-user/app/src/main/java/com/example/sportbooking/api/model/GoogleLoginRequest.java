package com.example.sportbooking.api.model;

import com.google.gson.annotations.SerializedName;

public class GoogleLoginRequest {
    @SerializedName("id_token")
    private final String idToken;

    public GoogleLoginRequest(String idToken) {
        this.idToken = idToken;
    }

    public String getIdToken() {
        return idToken;
    }
}

package com.example.sportbooking.api.model;

public class RegisterRequest {

    private final String full_name;
    private final String email;
    private final String password;

    public RegisterRequest(
            String fullName,
            String email,
            String password
    ) {
        this.full_name = fullName;
        this.email = email;
        this.password = password;
    }

    public String getFull_name() {
        return full_name;
    }

    public String getEmail() {
        return email;
    }

    public String getPassword() {
        return password;
    }
}
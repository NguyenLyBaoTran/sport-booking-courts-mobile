package com.example.sportbooking.api.model;

public class UserResponse {

    private int id;
    private String full_name;
    private String email;
    private String phone;
    private String role;
    private boolean is_active;
    private String created_at;

    public int getId() {
        return id;
    }

    public String getFull_name() {
        return full_name;
    }

    public String getEmail() {
        return email;
    }

    public String getPhone() {
        return phone;
    }

    public String getRole() {
        return role;
    }

    public boolean isActive() {
        return is_active;
    }

    public String getCreated_at() {
        return created_at;
    }
}
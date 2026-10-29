package com.example.sportbooking.api;

import com.example.sportbooking.api.model.LoginRequest;
import com.example.sportbooking.api.model.RegisterRequest;
import com.example.sportbooking.api.model.TokenResponse;
import com.example.sportbooking.api.model.UserResponse;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.Header;
import retrofit2.http.POST;

public interface AuthApi {

    @POST("api/v1/auth/register")
    Call<UserResponse> register(
            @Body RegisterRequest request
    );

    @POST("api/v1/auth/login")
    Call<TokenResponse> login(
            @Body LoginRequest request
    );

    @GET("api/v1/users/me")
    Call<UserResponse> getCurrentUser(
            @Header("Authorization") String authorization
    );
}
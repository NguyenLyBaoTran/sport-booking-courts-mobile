package com.example.sportbooking.api;

import com.example.sportbooking.api.model.ForgotPasswordRequest;
import com.example.sportbooking.api.model.LoginRequest;
import com.example.sportbooking.api.model.PasswordResetRequest;
import com.example.sportbooking.api.model.RegisterRequest;
import com.example.sportbooking.api.model.TokenResponse;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.api.model.UserUpdateRequest;
import com.google.gson.JsonObject;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.PATCH;
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

    @POST("api/v1/auth/google")
    Call<TokenResponse> googleLogin(
            @Body com.example.sportbooking.api.model.GoogleLoginRequest request
    );

    @POST("api/v1/auth/forgot-password")
    Call<JsonObject> requestForgotPasswordOtp(
            @Body ForgotPasswordRequest request
    );

    @POST("api/v1/auth/reset-password")
    Call<JsonObject> resetPassword(
            @Body PasswordResetRequest request
    );

    @GET("api/v1/users/me")
    Call<UserResponse> getCurrentUser();

    @PATCH("api/v1/users/me")
    Call<UserResponse> updateProfile(
            @Body UserUpdateRequest request
    );
}
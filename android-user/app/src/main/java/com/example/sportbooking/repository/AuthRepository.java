package com.example.sportbooking.repository;

import android.content.Context;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.LoginRequest;
import com.example.sportbooking.api.model.RegisterRequest;
import com.example.sportbooking.api.model.TokenResponse;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.auth.TokenStore;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class AuthRepository {

    private final Context context;
    private final AuthApi authApi;

    public AuthRepository(Context context) {
        this.context = context.getApplicationContext();
        this.authApi = ApiClient.getAuthApi(context);
    }

    public void login(
            LoginRequest request,
            ApiCallback<TokenResponse> callback
    ) {
        authApi.login(request).enqueue(new Callback<TokenResponse>() {
            @Override
            public void onResponse(
                    Call<TokenResponse> call,
                    Response<TokenResponse> response
            ) {
                if (response.isSuccessful() && response.body() != null) {
                    String token = response.body().getAccess_token();

                    if (token != null && !token.isEmpty()) {
                        TokenStore.saveToken(context, token);
                        callback.onSuccess(response.body());
                    } else {
                        callback.onError("Access token is missing.");
                    }
                } else {
                    callback.onError(
                            "Login failed. HTTP " + response.code()
                    );
                }
            }

            @Override
            public void onFailure(
                    Call<TokenResponse> call,
                    Throwable throwable
            ) {
                callback.onError(getErrorMessage(throwable));
            }
        });
    }

    public void register(
            RegisterRequest request,
            ApiCallback<UserResponse> callback
    ) {
        authApi.register(request).enqueue(new Callback<UserResponse>() {
            @Override
            public void onResponse(
                    Call<UserResponse> call,
                    Response<UserResponse> response
            ) {
                if (response.isSuccessful() && response.body() != null) {
                    callback.onSuccess(response.body());
                } else {
                    callback.onError(
                            "Registration failed. HTTP " + response.code()
                    );
                }
            }

            @Override
            public void onFailure(
                    Call<UserResponse> call,
                    Throwable throwable
            ) {
                callback.onError(getErrorMessage(throwable));
            }
        });
    }

    public void getCurrentUser(ApiCallback<UserResponse> callback) {
        String token = TokenStore.getToken(context);

        if (token == null || token.isEmpty()) {
            callback.onError("User is not logged in.");
            return;
        }

        authApi.getCurrentUser()
                .enqueue(new Callback<UserResponse>() {
                    @Override
                    public void onResponse(
                            Call<UserResponse> call,
                            Response<UserResponse> response
                    ) {
                        if (response.isSuccessful() && response.body() != null) {
                            callback.onSuccess(response.body());
                        } else {
                            callback.onError(
                                    "Unable to get user information. HTTP "
                                            + response.code()
                            );
                        }
                    }

                    @Override
                    public void onFailure(
                            Call<UserResponse> call,
                            Throwable throwable
                    ) {
                        callback.onError(getErrorMessage(throwable));
                    }
                });
    }

    public void logout() {
        TokenStore.clearToken(context);
    }

    private String getErrorMessage(Throwable throwable) {
        if (throwable == null || throwable.getMessage() == null) {
            return "Cannot connect to server.";
        }

        return throwable.getMessage();
    }
}
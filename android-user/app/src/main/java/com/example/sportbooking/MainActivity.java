package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.auth.TokenStore;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private AuthApi authApi;
    private boolean openingLogin = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        authApi = ApiClient.getAuthApi(this);
        String token = TokenStore.getToken(this);

        if (TextUtils.isEmpty(token)) {
            openLogin();
        } else {
            validateToken(token);
        }
    }

    private void validateToken(String token) {
        authApi.getCurrentUser()
                .enqueue(new Callback<UserResponse>() {
                    @Override
                    public void onResponse(
                            Call<UserResponse> call,
                            Response<UserResponse> response
                    ) {
                        if (response.isSuccessful()
                                && response.body() != null
                                && "USER".equals(response.body().getRole())
                                && response.body().isActive()) {
                            String fullName = response.body().getFull_name();
                            if (fullName != null && !fullName.trim().isEmpty()) {
                                getSharedPreferences("user_profile_prefs", MODE_PRIVATE)
                                        .edit().putString("saved_full_name", fullName.trim()).apply();
                            }
                            showHome();
                            return;
                        }

                        TokenStore.clearToken(MainActivity.this);
                        openLogin();
                    }

                    @Override
                    public void onFailure(
                            Call<UserResponse> call,
                            Throwable throwable
                    ) {
                        TokenStore.clearToken(MainActivity.this);
                        openLogin();
                    }
                });
    }

    private void showHome() {
        Intent intent = new Intent(this, CourtSearchActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(intent);
        finish();
    }

    private void openLogin() {
        if (openingLogin || isFinishing()) {
            return;
        }

        openingLogin = true;

        Intent intent = new Intent(
                MainActivity.this,
                LoginActivity.class
        );

        intent.setFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TASK
        );

        startActivity(intent);
        finish();
    }
}

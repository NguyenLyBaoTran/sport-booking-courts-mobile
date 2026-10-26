
package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

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

        authApi = ApiClient.getAuthApi();

        String token = TokenStore.getToken(this);

        if (TextUtils.isEmpty(token)) {
            openLogin();
        } else {
            validateToken(token);
        }
    }

    private void validateToken(String token) {
        authApi.getCurrentUser("Bearer " + token)
                .enqueue(new Callback<UserResponse>() {
                    @Override
                    public void onResponse(
                            Call<UserResponse> call,
                            Response<UserResponse> response
                    ) {
                        if (response.isSuccessful()
                                && response.body() != null) {
                            showHome(response.body());
                            return;
                        }

                        if (response.code() == 401) {
                            TokenStore.clear(MainActivity.this);
                            openLogin();
                            return;
                        }

                        showHome(null);
                    }

                    @Override
                    public void onFailure(
                            Call<UserResponse> call,
                            Throwable throwable
                    ) {
                        showHome(null);
                        Toast.makeText(
                                MainActivity.this,
                                "Cannot verify session. Check your connection.",
                                Toast.LENGTH_LONG
                        ).show();
                    }
                });
    }

    private void showHome(UserResponse user) {
        setContentView(R.layout.activity_main);

        TextView tvWelcome = findViewById(R.id.tvWelcome);
        Button btnFindCourt = findViewById(R.id.btnFindCourt);
        Button btnMyBookings = findViewById(R.id.btnMyBookings);
        Button btnProfile = findViewById(R.id.btnProfile);
        Button btnLogout = findViewById(R.id.btnLogout);

        String name = null;

        if (user != null) {
            name = user.getFull_name();

            if (TextUtils.isEmpty(name)) {
                name = user.getEmail();
            }
        }

        tvWelcome.setText(
                TextUtils.isEmpty(name)
                        ? "Welcome to Sport Booking!"
                        : "Welcome, " + name + "!"
        );

        btnFindCourt.setOnClickListener(v ->
                Toast.makeText(
                        this,
                        "Court search will be available soon.",
                        Toast.LENGTH_SHORT
                ).show()
        );

        btnMyBookings.setOnClickListener(v ->
                Toast.makeText(
                        this,
                        "My bookings will be available soon.",
                        Toast.LENGTH_SHORT
                ).show()
        );

        btnProfile.setOnClickListener(v ->
                Toast.makeText(
                        this,
                        "Profile will be available soon.",
                        Toast.LENGTH_SHORT
                ).show()
        );

        btnLogout.setOnClickListener(v -> {
            TokenStore.clear(this);
            openLogin();
        });
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

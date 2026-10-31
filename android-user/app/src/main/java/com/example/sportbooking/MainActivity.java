package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AlertDialog;
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
                                && response.body() != null) {
                            showHome(response.body());
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
                    }
                });
    }

    private void showHome(UserResponse user) {
        setContentView(R.layout.activity_main);

        TextView tvWelcome = findViewById(R.id.tvWelcome);
        View btnFindCourt = findViewById(R.id.btnFindCourt);
        View btnMyBookings = findViewById(R.id.btnMyBookings);
        View btnProfile = findViewById(R.id.imgProfileIcon);
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
                startActivity(new Intent(this, CourtSearchActivity.class))
        );

        btnMyBookings.setOnClickListener(v ->
                startActivity(new Intent(this, BookingsActivity.class))
        );

        View cardBadminton = findViewById(R.id.cardBadminton);
        View cardTennis = findViewById(R.id.cardTennis);
        View cardBasketball = findViewById(R.id.cardBasketball);
        View cardFootball = findViewById(R.id.cardFootball);

        if (cardBadminton != null) {
            cardBadminton.setOnClickListener(v -> {
                Intent intent = new Intent(this, CourtSearchActivity.class);
                intent.putExtra("sport_name", "Badminton");
                startActivity(intent);
            });
        }
        if (cardTennis != null) {
            cardTennis.setOnClickListener(v -> {
                Intent intent = new Intent(this, CourtSearchActivity.class);
                intent.putExtra("sport_name", "Tennis");
                startActivity(intent);
            });
        }
        if (cardBasketball != null) {
            cardBasketball.setOnClickListener(v -> {
                Intent intent = new Intent(this, CourtSearchActivity.class);
                intent.putExtra("sport_name", "Basketball");
                startActivity(intent);
            });
        }
        if (cardFootball != null) {
            cardFootball.setOnClickListener(v -> {
                Intent intent = new Intent(this, CourtSearchActivity.class);
                intent.putExtra("sport_name", "Football");
                startActivity(intent);
            });
        }

        btnProfile.setOnClickListener(v -> {
            String profileName = user == null ? "Unknown user" : user.getFull_name();
            String profileEmail = user == null ? "Session verified" : user.getEmail();
            new AlertDialog.Builder(this)
                    .setTitle(TextUtils.isEmpty(profileName) ? "My Profile" : profileName)
                    .setMessage(TextUtils.isEmpty(profileEmail) ? "No profile details returned." : profileEmail)
                    .setPositiveButton("Close", null)
                    .show();
        });

        btnLogout.setOnClickListener(v -> {
            TokenStore.clearToken(this);
            openLogin();
        });

        View navSearch = findViewById(R.id.navSearch);
        View navBookings = findViewById(R.id.navBookings);
        View navProfile = findViewById(R.id.navProfile);

        if (navSearch != null) {
            navSearch.setOnClickListener(v -> startActivity(new Intent(this, CourtSearchActivity.class)));
        }
        if (navBookings != null) {
            navBookings.setOnClickListener(v -> startActivity(new Intent(this, BookingsActivity.class)));
        }
        if (navProfile != null) {
            navProfile.setOnClickListener(v -> btnProfile.performClick());
        }
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

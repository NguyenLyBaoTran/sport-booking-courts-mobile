package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.api.model.UserUpdateRequest;
import com.example.sportbooking.auth.TokenStore;
import com.example.sportbooking.utils.BottomNavUtils;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ProfileActivity extends AppCompatActivity {

    private AuthApi authApi;
    private TextView tvProfileName, tvProfileEmail;
    private EditText etFullName, etEmail, etPhone;
    private Button btnSaveProfile, btnLogout;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_profile);

        authApi = ApiClient.getAuthApi(this);

        tvProfileName = findViewById(R.id.tvProfileName);
        tvProfileEmail = findViewById(R.id.tvProfileEmail);
        etFullName = findViewById(R.id.etFullName);
        etEmail = findViewById(R.id.etEmail);
        etPhone = findViewById(R.id.etPhone);
        btnSaveProfile = findViewById(R.id.btnSaveProfile);
        btnLogout = findViewById(R.id.btnLogout);

        BottomNavUtils.setupBottomNav(this, R.id.navProfile);

        loadUserProfile();

        btnSaveProfile.setOnClickListener(v -> saveProfile());

        btnLogout.setOnClickListener(v -> {
            TokenStore.clearToken(this);
            getSharedPreferences("user_profile_prefs", MODE_PRIVATE).edit().clear().apply();
            Intent intent = new Intent(this, LoginActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
            finish();
        });
    }

    private void saveProfile() {
        String name = etFullName.getText().toString().trim();
        String phone = etPhone.getText().toString().trim();

        if (TextUtils.isEmpty(name)) {
            Toast.makeText(this, "Please enter your full name", Toast.LENGTH_SHORT).show();
            return;
        }

        btnSaveProfile.setEnabled(false);

        authApi.updateProfile(new UserUpdateRequest(name, phone)).enqueue(new Callback<UserResponse>() {
            @Override
            public void onResponse(Call<UserResponse> call, Response<UserResponse> response) {
                btnSaveProfile.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    UserResponse updated = response.body();
                    String updatedName = updated.getFull_name();
                    String updatedPhone = updated.getPhone();

                    tvProfileName.setText(updatedName);

                    getSharedPreferences("user_profile_prefs", MODE_PRIVATE)
                            .edit()
                            .putString("saved_full_name", updatedName)
                            .putString("saved_phone", updatedPhone)
                            .apply();

                    Toast.makeText(ProfileActivity.this, "Profile updated successfully!", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(ProfileActivity.this, "Failed to update profile", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<UserResponse> call, Throwable t) {
                btnSaveProfile.setEnabled(true);
                // Fallback to local save if offline
                tvProfileName.setText(name);
                getSharedPreferences("user_profile_prefs", MODE_PRIVATE)
                        .edit()
                        .putString("saved_full_name", name)
                        .putString("saved_phone", phone)
                        .apply();
                Toast.makeText(ProfileActivity.this, "Saved locally (offline)", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void loadUserProfile() {
        String savedName = getSharedPreferences("user_profile_prefs", MODE_PRIVATE).getString("saved_full_name", null);
        String savedPhone = getSharedPreferences("user_profile_prefs", MODE_PRIVATE).getString("saved_phone", null);

        authApi.getCurrentUser().enqueue(new Callback<UserResponse>() {
            @Override
            public void onResponse(Call<UserResponse> call, Response<UserResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    UserResponse user = response.body();
                    String name = !TextUtils.isEmpty(user.getFull_name()) ? user.getFull_name() : (savedName != null ? savedName : "");
                    String email = user.getEmail();
                    String phone = !TextUtils.isEmpty(user.getPhone()) ? user.getPhone() : (savedPhone != null ? savedPhone : "");

                    tvProfileName.setText(!TextUtils.isEmpty(name) ? name : "Customer");
                    tvProfileEmail.setText(!TextUtils.isEmpty(email) ? email : "");
                    etFullName.setText(!TextUtils.isEmpty(name) ? name : "");
                    etEmail.setText(!TextUtils.isEmpty(email) ? email : "");
                    etPhone.setText(!TextUtils.isEmpty(phone) ? phone : "");

                    getSharedPreferences("user_profile_prefs", MODE_PRIVATE)
                            .edit()
                            .putString("saved_full_name", name)
                            .putString("saved_phone", phone)
                            .apply();
                } else if (savedName != null) {
                    tvProfileName.setText(savedName);
                    etFullName.setText(savedName);
                    if (savedPhone != null) etPhone.setText(savedPhone);
                }
            }

            @Override
            public void onFailure(Call<UserResponse> call, Throwable t) {
                if (savedName != null) {
                    tvProfileName.setText(savedName);
                    etFullName.setText(savedName);
                    if (savedPhone != null) etPhone.setText(savedPhone);
                }
            }
        });
    }
}

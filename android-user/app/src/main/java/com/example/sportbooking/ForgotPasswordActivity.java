package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.ForgotPasswordRequest;
import com.example.sportbooking.api.model.PasswordResetRequest;
import com.example.sportbooking.utils.ApiUtils;
import com.google.gson.JsonObject;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ForgotPasswordActivity extends AppCompatActivity {

    private EditText etResetEmail, etOtpCode, etNewPassword, etConfirmPassword;
    private Button btnSendOtp, btnResetPassword;
    private View layoutOtpReset;
    private ProgressBar progressBar;
    private TextView tvResetInfo, tvResetError;
    private AuthApi authApi;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_forgot_password);

        authApi = ApiClient.getAuthApi(this);

        etResetEmail = findViewById(R.id.etResetEmail);
        etOtpCode = findViewById(R.id.etOtpCode);
        etNewPassword = findViewById(R.id.etNewPassword);
        etConfirmPassword = findViewById(R.id.etConfirmPassword);
        btnSendOtp = findViewById(R.id.btnSendOtp);
        btnResetPassword = findViewById(R.id.btnResetPassword);
        layoutOtpReset = findViewById(R.id.layoutOtpReset);
        progressBar = findViewById(R.id.progressBar);
        tvResetInfo = findViewById(R.id.tvResetInfo);
        tvResetError = findViewById(R.id.tvResetError);

        ImageView btnBack = findViewById(R.id.btnBack);
        if (btnBack != null) {
            btnBack.setOnClickListener(v -> finish());
        }

        btnSendOtp.setOnClickListener(v -> handleSendOtp());
        btnResetPassword.setOnClickListener(v -> handleResetPassword());
    }

    private void handleSendOtp() {
        String email = etResetEmail.getText().toString().trim().toLowerCase();

        if (TextUtils.isEmpty(email)) {
            showError("Please enter your registered email address.");
            return;
        }

        setLoading(true);

        authApi.requestForgotPasswordOtp(new ForgotPasswordRequest(email))
                .enqueue(new Callback<JsonObject>() {
                    @Override
                    public void onResponse(Call<JsonObject> call, Response<JsonObject> response) {
                        setLoading(false);
                        if (response.isSuccessful() && response.body() != null) {
                            if (layoutOtpReset != null) {
                                layoutOtpReset.setVisibility(View.VISIBLE);
                            }
                            showInfo("If this email has an account, a reset code was sent. Check your inbox and spam folder.");
                        } else {
                            showError(ApiUtils.getErrorMessage(response));
                        }
                    }

                    @Override
                    public void onFailure(Call<JsonObject> call, Throwable t) {
                        setLoading(false);
                        showError("Cannot connect to server. Check network and try again.");
                    }
                });
    }

    private void handleResetPassword() {
        String email = etResetEmail.getText().toString().trim().toLowerCase();
        String otpCode = etOtpCode.getText().toString().trim();
        String newPassword = etNewPassword.getText().toString();
        String confirmPassword = etConfirmPassword.getText().toString();

        if (TextUtils.isEmpty(email) || TextUtils.isEmpty(otpCode)
                || TextUtils.isEmpty(newPassword) || TextUtils.isEmpty(confirmPassword)) {
            showError("All fields are required.");
            return;
        }

        if (otpCode.length() != 6) {
            showError("OTP code must be 6 digits.");
            return;
        }

        if (newPassword.length() < 8) {
            showError("Password must be at least 8 characters.");
            return;
        }

        if (!newPassword.equals(confirmPassword)) {
            showError("Passwords do not match.");
            return;
        }

        setLoading(true);

        authApi.resetPassword(new PasswordResetRequest(email, otpCode, newPassword))
                .enqueue(new Callback<JsonObject>() {
                    @Override
                    public void onResponse(Call<JsonObject> call, Response<JsonObject> response) {
                        setLoading(false);
                        if (response.isSuccessful()) {
                            Toast.makeText(ForgotPasswordActivity.this, "Password reset successfully!", Toast.LENGTH_LONG).show();
                            Intent intent = new Intent(ForgotPasswordActivity.this, LoginActivity.class);
                            intent.putExtra("registered_email", email);
                            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                            startActivity(intent);
                            finish();
                        } else {
                            showError(ApiUtils.getErrorMessage(response));
                        }
                    }

                    @Override
                    public void onFailure(Call<JsonObject> call, Throwable t) {
                        setLoading(false);
                        showError("Cannot connect to server. Check network and try again.");
                    }
                });
    }

    private void setLoading(boolean loading) {
        btnSendOtp.setEnabled(!loading);
        btnResetPassword.setEnabled(!loading);
        progressBar.setVisibility(loading ? View.VISIBLE : View.GONE);
        if (loading) {
            showError("");
        }
    }

    private void showInfo(String message) {
        tvResetInfo.setText(message);
        tvResetInfo.setVisibility(TextUtils.isEmpty(message) ? View.GONE : View.VISIBLE);
        tvResetError.setVisibility(View.GONE);
    }

    private void showError(String message) {
        tvResetError.setText(message);
        tvResetError.setVisibility(TextUtils.isEmpty(message) ? View.GONE : View.VISIBLE);
    }
}

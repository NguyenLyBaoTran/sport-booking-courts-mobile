package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Patterns;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.LoginRequest;
import com.example.sportbooking.api.model.TokenResponse;
import com.example.sportbooking.auth.TokenStore;

import org.json.JSONObject;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class LoginActivity extends AppCompatActivity {

    private EditText etEmail;
    private EditText etPassword;
    private Button btnLogin;
    private ProgressBar progressBar;
    private TextView tvError;
    private AuthApi authApi;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.login_screen);

        authApi = ApiClient.getAuthApi();

        etEmail = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);
        btnLogin = findViewById(R.id.btnLogin);
        progressBar = findViewById(R.id.progressBar);
        tvError = findViewById(R.id.tvError);

        String registeredEmail =
                getIntent().getStringExtra("registered_email");

        if (registeredEmail != null) {
            etEmail.setText(registeredEmail);
        }

        btnLogin.setOnClickListener(v -> login());

        View tabRegister = findViewById(R.id.tabRegister);
        View tvGoRegister = findViewById(R.id.tvGoRegister);

        if (tabRegister != null) {
            tabRegister.setOnClickListener(v -> openRegister());
        }

        if (tvGoRegister != null) {
            tvGoRegister.setOnClickListener(v -> openRegister());
        }
    }

    private void login() {
        String email = etEmail.getText()
                .toString()
                .trim()
                .toLowerCase();

        String password = etPassword.getText().toString();

        if (TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
            showError(getString(R.string.error_required));
            return;
        }

        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            showError(getString(R.string.error_invalid_email));
            return;
        }

        setLoading(true);

        authApi.login(new LoginRequest(email, password))
                .enqueue(new Callback<TokenResponse>() {
                    @Override
                    public void onResponse(
                            Call<TokenResponse> call,
                            Response<TokenResponse> response
                    ) {
                        setLoading(false);

                        if (!response.isSuccessful()
                                || response.body() == null) {
                            showError(getErrorMessage(response));
                            return;
                        }

                        String token =
                                response.body().getAccess_token();

                        if (TextUtils.isEmpty(token)) {
                            showError(
                                    "The server did not return an access token."
                            );
                            return;
                        }

                        TokenStore.saveToken(
                                LoginActivity.this,
                                token
                        );

                        Intent intent = new Intent(
                                LoginActivity.this,
                                MainActivity.class
                        );

                        intent.setFlags(
                                Intent.FLAG_ACTIVITY_NEW_TASK
                                        | Intent.FLAG_ACTIVITY_CLEAR_TASK
                        );

                        startActivity(intent);
                        finish();
                    }

                    @Override
                    public void onFailure(
                            Call<TokenResponse> call,
                            Throwable throwable
                    ) {
                        setLoading(false);

                        showError(
                                "Cannot connect to the server. "
                                        + "Check your network and backend."
                        );
                    }
                });
    }

    private void openRegister() {
        startActivity(
                new Intent(this, RegisterActivity.class)
        );
    }

    private void setLoading(boolean loading) {
        btnLogin.setEnabled(!loading);

        progressBar.setVisibility(
                loading ? View.VISIBLE : View.GONE
        );

        if (loading) {
            showError("");
        }
    }

    private void showError(String message) {
        tvError.setText(message);

        tvError.setVisibility(
                TextUtils.isEmpty(message)
                        ? View.GONE
                        : View.VISIBLE
        );
    }

    private String getErrorMessage(Response<?> response) {
        if (response.code() == 401) {
            return "Email or password is incorrect.";
        }

        if (response.errorBody() == null) {
            return "Unable to log in. Please try again.";
        }

        try {
            String body = response.errorBody().string();
            JSONObject json = new JSONObject(body);
            String detail = json.optString("detail", "");

            if (!TextUtils.isEmpty(detail)) {
                return detail;
            }
        } catch (Exception ignored) {
            return "Unable to log in. Please try again.";
        }

        return "Unable to log in. Please try again.";
    }
}

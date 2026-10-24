package com.example.sportbooking;

import android.os.Bundle;
import android.text.TextUtils;
import android.util.Patterns;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private boolean isRegisterScreen = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showLoginScreen();
    }

    private void showLoginScreen() {
        isRegisterScreen = false;
        setContentView(R.layout.login_screen);

        View tabRegister = findViewById(R.id.tabRegister);
        View tvGoRegister = findViewById(R.id.tvGoRegister);

        if (tabRegister != null) {
            tabRegister.setOnClickListener(v -> showRegisterScreen());
        }

        if (tvGoRegister != null) {
            tvGoRegister.setOnClickListener(v -> showRegisterScreen());
        }

        Button btnLogin = findViewById(R.id.btnLogin);

        if (btnLogin != null) {
            btnLogin.setOnClickListener(v -> validateLogin());
        }
    }

    private void showRegisterScreen() {
        isRegisterScreen = true;
        setContentView(R.layout.register_screen);

        View tvGoLogin = findViewById(R.id.tvGoLogin);
        View tvGoLoginBottom = findViewById(R.id.tvGoLoginBottom);

        if (tvGoLogin != null) {
            tvGoLogin.setOnClickListener(v -> showLoginScreen());
        }

        if (tvGoLoginBottom != null) {
            tvGoLoginBottom.setOnClickListener(v -> showLoginScreen());
        }

        Button btnRegister = findViewById(R.id.btnRegister);

        if (btnRegister != null) {
            btnRegister.setOnClickListener(v -> validateRegister());
        }
    }

    private void validateLogin() {
        EditText etEmail = findViewById(R.id.etEmail);
        EditText etPassword = findViewById(R.id.etPassword);

        String email = etEmail.getText().toString().trim();
        String password = etPassword.getText().toString();

        if (TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
            showToast(getString(R.string.error_required));
            return;
        }

        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            showToast(getString(R.string.error_invalid_email));
            return;
        }

        showToast("Login API is not connected yet");
    }

    private void validateRegister() {
        EditText etFullName = findViewById(R.id.etFullName);
        EditText etEmail = findViewById(R.id.etEmail);
        EditText etPassword = findViewById(R.id.etPassword);
        EditText etConfirmPassword = findViewById(R.id.etConfirmPassword);
        TextView tvError = findViewById(R.id.tvError);

        String fullName = etFullName.getText().toString().trim();
        String email = etEmail.getText().toString().trim().toLowerCase();
        String password = etPassword.getText().toString();
        String confirmPassword = etConfirmPassword.getText().toString();

        tvError.setVisibility(View.VISIBLE);

        if (TextUtils.isEmpty(fullName)
                || TextUtils.isEmpty(email)
                || TextUtils.isEmpty(password)
                || TextUtils.isEmpty(confirmPassword)) {
            tvError.setText(R.string.error_required);
            return;
        }

        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            tvError.setText(R.string.error_invalid_email);
            return;
        }

        if (password.length() < 8 || password.length() > 128) {
            tvError.setText(R.string.error_password_length);
            return;
        }

        if (!password.equals(confirmPassword)) {
            tvError.setText(R.string.error_password_mismatch);
            return;
        }

        tvError.setVisibility(View.GONE);
        showToast("Register API is not connected yet");
    }

    private void showToast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onBackPressed() {
        if (isRegisterScreen) {
            showLoginScreen();
        } else {
            super.onBackPressed();
        }
    }
}

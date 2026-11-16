package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Patterns;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.fragment.app.Fragment;
import android.view.LayoutInflater;
import android.view.ViewGroup;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.RegisterRequest;
import com.example.sportbooking.api.model.UserResponse;

import org.json.JSONObject;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class RegisterFragment extends Fragment {

    private EditText etFullName;
    private EditText etEmail;
    private EditText etPassword;
    private EditText etConfirmPassword;
    private Button btnRegister;
    private TextView tvError;
    private AuthApi authApi;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        return inflater.inflate(R.layout.register_screen, container, false);
    }

    @Override
    public void onViewCreated(View root, Bundle savedInstanceState) {
        super.onViewCreated(root, savedInstanceState);
        authApi = ApiClient.getAuthApi(requireContext());
        etFullName = root.findViewById(R.id.etFullName);
        etEmail = root.findViewById(R.id.etEmail);
        etPassword = root.findViewById(R.id.etPassword);
        etConfirmPassword = root.findViewById(R.id.etConfirmPassword);
        btnRegister = root.findViewById(R.id.btnRegister);
        tvError = root.findViewById(R.id.tvError);
        btnRegister.setOnClickListener(v -> register());
        View tvGoLogin = root.findViewById(R.id.tvGoLogin);
        View tvGoLoginBottom = root.findViewById(R.id.tvGoLoginBottom);
        if (tvGoLogin != null) tvGoLogin.setOnClickListener(v -> ((AuthActivity) requireActivity()).showLogin(null));
        if (tvGoLoginBottom != null) tvGoLoginBottom.setOnClickListener(v -> ((AuthActivity) requireActivity()).showLogin(null));
    }

    private void register() {
        String fullName = etFullName.getText()
                .toString()
                .trim();

        String email = etEmail.getText()
                .toString()
                .trim()
                .toLowerCase();

        String password = etPassword.getText().toString();

        String confirmPassword =
                etConfirmPassword.getText().toString();

        if (TextUtils.isEmpty(fullName)
                || TextUtils.isEmpty(email)
                || TextUtils.isEmpty(password)
                || TextUtils.isEmpty(confirmPassword)) {
            showError(getString(R.string.error_required));
            return;
        }

        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            showError(getString(R.string.error_invalid_email));
            return;
        }

        if (password.length() < 8 || password.length() > 128) {
            showError(getString(R.string.error_password_length));
            return;
        }

        if (!password.equals(confirmPassword)) {
            showError(getString(R.string.error_password_mismatch));
            return;
        }

        setLoading(true);

        RegisterRequest request =
                new RegisterRequest(fullName, email, password);

        authApi.register(request).enqueue(new Callback<UserResponse>() {
            @Override
            public void onResponse(
                    Call<UserResponse> call,
                    Response<UserResponse> response
            ) {
                setLoading(false);

                if (response.code() == 201 && response.body() != null) {
                    Toast.makeText(
                            requireContext(),
                            "Account created. Please log in.",
                            Toast.LENGTH_LONG
                    ).show();

                    ((AuthActivity) requireActivity()).showLogin(email);
                    return;
                }

                showError(getErrorMessage(response));
            }

            @Override
            public void onFailure(
                    Call<UserResponse> call,
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

    private void setLoading(boolean loading) {
        btnRegister.setEnabled(!loading);

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
        if (response.code() == 409) {
            return "This email is already registered.";
        }

        if (response.errorBody() == null) {
            return "Unable to create account. Please try again.";
        }

        try {
            String body = response.errorBody().string();
            JSONObject json = new JSONObject(body);
            String detail = json.optString("detail", "");

            if (!TextUtils.isEmpty(detail)) {
                return detail;
            }
        } catch (Exception ignored) {
            return "Unable to create account. Please try again.";
        }

        return "Unable to create account. Please try again.";
    }
}

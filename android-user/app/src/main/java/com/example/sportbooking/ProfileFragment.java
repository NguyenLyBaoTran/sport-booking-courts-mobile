package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.api.model.UserUpdateRequest;
import com.example.sportbooking.auth.TokenStore;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ProfileFragment extends Fragment {

    private AuthApi authApi;
    private TextView tvProfileName, tvProfileEmail;
    private EditText etFullName, etEmail, etPhone;
    private Button btnSaveProfile, btnLogout;

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View root = inflater.inflate(R.layout.activity_profile, container, false);

        authApi = ApiClient.getAuthApi(requireContext());

        tvProfileName = root.findViewById(R.id.tvProfileName);
        tvProfileEmail = root.findViewById(R.id.tvProfileEmail);
        etFullName = root.findViewById(R.id.etFullName);
        etEmail = root.findViewById(R.id.etEmail);
        etPhone = root.findViewById(R.id.etPhone);
        btnSaveProfile = root.findViewById(R.id.btnSaveProfile);
        btnLogout = root.findViewById(R.id.btnLogout);

        loadUserProfile();

        btnSaveProfile.setOnClickListener(v -> saveProfile());

        btnLogout.setOnClickListener(v -> {
            TokenStore.clearToken(requireContext());
            requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE).edit().clear().apply();
            Intent intent = new Intent(requireContext(), AuthActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
            requireActivity().finish();
        });
        return root;
    }

    private void saveProfile() {
        String name = etFullName.getText().toString().trim();
        String phone = etPhone.getText().toString().trim();

        if (TextUtils.isEmpty(name)) {
            Toast.makeText(requireContext(), "Please enter your full name", Toast.LENGTH_SHORT).show();
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

                    requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE)
                            .edit()
                            .putString("saved_full_name", updatedName)
                            .putString("saved_phone", updatedPhone)
                            .apply();
                    ((MainActivity) requireActivity()).refreshHomeGreeting();

                    Toast.makeText(requireContext(), "Profile updated successfully!", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(requireContext(), "Failed to update profile", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<UserResponse> call, Throwable t) {
                btnSaveProfile.setEnabled(true);
                // Fallback to local save if offline
                tvProfileName.setText(name);
                requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE)
                        .edit()
                        .putString("saved_full_name", name)
                        .putString("saved_phone", phone)
                        .apply();
                ((MainActivity) requireActivity()).refreshHomeGreeting();
                Toast.makeText(requireContext(), "Saved locally (offline)", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void loadUserProfile() {
        String savedName = requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE).getString("saved_full_name", null);
        String savedPhone = requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE).getString("saved_phone", null);

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

                    requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE)
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

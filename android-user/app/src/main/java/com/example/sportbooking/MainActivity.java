package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.auth.TokenStore;
import com.example.sportbooking.utils.BottomNavUtils;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    public static final String EXTRA_OPEN_HISTORY = "open_history_after_booking";
    private static final String TAG_HOME = "customer_home";
    private static final String TAG_HISTORY = "customer_history";
    private static final String TAG_PROFILE = "customer_profile";
    private int selectedTabId = R.id.navHome;
    private HomeFragment homeFragment;
    private HistoryFragment historyFragment;
    private ProfileFragment profileFragment;
    private Bundle restoreState;

    private AuthApi authApi;
    private boolean openingLogin = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        restoreState = savedInstanceState;

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
        setContentView(R.layout.activity_customer_main);
        FragmentManager manager = getSupportFragmentManager();
        homeFragment = (HomeFragment) manager.findFragmentByTag(TAG_HOME);
        historyFragment = (HistoryFragment) manager.findFragmentByTag(TAG_HISTORY);
        profileFragment = (ProfileFragment) manager.findFragmentByTag(TAG_PROFILE);
        FragmentTransaction transaction = manager.beginTransaction();
        boolean added = false;
        if (homeFragment == null) {
            homeFragment = new HomeFragment();
            transaction.add(R.id.customerContent, homeFragment, TAG_HOME);
            added = true;
        }
        if (historyFragment == null) {
            historyFragment = new HistoryFragment();
            transaction.add(R.id.customerContent, historyFragment, TAG_HISTORY).hide(historyFragment);
            added = true;
        }
        if (profileFragment == null) {
            profileFragment = new ProfileFragment();
            transaction.add(R.id.customerContent, profileFragment, TAG_PROFILE).hide(profileFragment);
            added = true;
        }
        if (added) transaction.setReorderingAllowed(true).commitNow();
        if (restoreState != null) selectedTabId = restoreState.getInt("selected_customer_tab", R.id.navHome);
        if (getIntent().getBooleanExtra(EXTRA_OPEN_HISTORY, false)) selectedTabId = R.id.navBookings;
        selectTab(selectedTabId);
    }

    public void selectTab(int tabId) {
        int requested = tabId == R.id.navBookings || tabId == R.id.navProfile ? tabId : R.id.navHome;
        if (requested == selectedTabId && getSupportFragmentManager().findFragmentByTag(TAG_HOME) != null) {
            BottomNavUtils.setupBottomNav(this, selectedTabId);
            return;
        }
        Fragment target;
        if (requested == R.id.navBookings) { selectedTabId = requested; target = historyFragment; }
        else if (requested == R.id.navProfile) { selectedTabId = requested; target = profileFragment; }
        else { selectedTabId = R.id.navHome; target = homeFragment; }
        if (target == null) return;
        FragmentManager manager = getSupportFragmentManager();
        FragmentTransaction transaction = manager.beginTransaction();
        if (homeFragment != null) transaction.hide(homeFragment);
        if (historyFragment != null) transaction.hide(historyFragment);
        if (profileFragment != null) transaction.hide(profileFragment);
        transaction.setReorderingAllowed(true).show(target).commit();
        BottomNavUtils.setupBottomNav(this, selectedTabId);
    }

    @Override
    protected void onSaveInstanceState(@androidx.annotation.NonNull Bundle outState) {
        outState.putInt("selected_customer_tab", selectedTabId);
        super.onSaveInstanceState(outState);
    }

    public void refreshHomeGreeting() {
        if (homeFragment != null) homeFragment.refreshGreeting();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent.getBooleanExtra(EXTRA_OPEN_HISTORY, false)) {
            selectTab(R.id.navBookings);
            if (historyFragment != null) historyFragment.refreshBookings();
        }
    }

    @Override
    public void onBackPressed() {
        if (selectedTabId != R.id.navHome) {
            selectTab(R.id.navHome);
            return;
        }
        super.onBackPressed();
    }

    private void openLogin() {
        if (openingLogin || isFinishing()) {
            return;
        }

        openingLogin = true;

        Intent intent = new Intent(
                MainActivity.this,
                AuthActivity.class
        );

        intent.setFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TASK
        );

        startActivity(intent);
        finish();
    }
}

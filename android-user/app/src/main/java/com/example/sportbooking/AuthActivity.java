package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;

public class AuthActivity extends AppCompatActivity {
    private static final String TAG_LOGIN = "auth_login";
    private static final String TAG_REGISTER = "auth_register";
    private LoginFragment loginFragment;
    private RegisterFragment registerFragment;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_auth);
        FragmentManager manager = getSupportFragmentManager();
        loginFragment = (LoginFragment) manager.findFragmentByTag(TAG_LOGIN);
        registerFragment = (RegisterFragment) manager.findFragmentByTag(TAG_REGISTER);
        FragmentTransaction transaction = manager.beginTransaction();
        boolean changed = false;
        if (loginFragment == null) {
            Bundle arguments = new Bundle();
            String email = getIntent().getStringExtra("registered_email");
            if (email != null) arguments.putString("registered_email", email);
            loginFragment = new LoginFragment();
            loginFragment.setArguments(arguments);
            transaction.add(R.id.authContent, loginFragment, TAG_LOGIN);
            changed = true;
        }
        if (registerFragment == null) {
            registerFragment = new RegisterFragment();
            transaction.add(R.id.authContent, registerFragment, TAG_REGISTER).hide(registerFragment);
            changed = true;
        }
        if (changed) transaction.setReorderingAllowed(true).commitNow();
        if (getIntent().getStringExtra("registered_email") != null) showLogin(getIntent().getStringExtra("registered_email"));
    }

    public void showRegister() {
        showFragment(registerFragment);
    }

    public void showLogin(String email) {
        if (loginFragment != null) loginFragment.setRegisteredEmail(email);
        showFragment(loginFragment);
    }

    private void showFragment(Fragment target) {
        if (target == null) return;
        FragmentManager manager = getSupportFragmentManager();
        FragmentTransaction transaction = manager.beginTransaction();
        if (loginFragment != null) transaction.hide(loginFragment);
        if (registerFragment != null) transaction.hide(registerFragment);
        transaction.show(target).setReorderingAllowed(true).commit();
    }

    public void onLoginSuccess() {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        startActivity(intent);
        finish();
    }

    @Override
    protected void onNewIntent(@NonNull Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        showLogin(intent.getStringExtra("registered_email"));
    }

    @Override
    public void onBackPressed() {
        if (registerFragment != null && registerFragment.isVisible()) {
            showLogin(null);
            return;
        }
        super.onBackPressed();
    }
}

package com.example.sportbooking.auth;

import android.content.Context;
import android.content.SharedPreferences;

public final class TokenStore {

    private static final String PREFS_NAME = "sport_booking_auth";
    private static final String KEY_ACCESS_TOKEN = "access_token";

    private TokenStore() {
    }

    public static void saveToken(Context context, String token) {
        preferences(context)
                .edit()
                .putString(KEY_ACCESS_TOKEN, token)
                .apply();
    }

    public static String getToken(Context context) {
        return preferences(context)
                .getString(KEY_ACCESS_TOKEN, null);
    }

    public static void clear(Context context) {
        preferences(context)
                .edit()
                .remove(KEY_ACCESS_TOKEN)
                .apply();
    }

    private static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(
                PREFS_NAME,
                Context.MODE_PRIVATE
        );
    }
}
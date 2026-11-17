package com.example.sportbooking.auth;

import android.content.Context;
import android.content.SharedPreferences;

public final class TokenStore {

    private static final String PREF_NAME = "sport_booking_auth";
    private static final String KEY_ACCESS_TOKEN = "access_token";

    private TokenStore() {
    }

    private static SharedPreferences getPreferences(Context context) {
        return context.getApplicationContext()
                .getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public static void saveToken(Context context, String token) {
        getPreferences(context)
                .edit()
                .putString(KEY_ACCESS_TOKEN, token)
                .apply();
    }

    public static String getToken(Context context) {
        return getPreferences(context)
                .getString(KEY_ACCESS_TOKEN, null);
    }

    public static boolean hasToken(Context context) {
        String token = getToken(context);
        return token != null && !token.trim().isEmpty();
    }

    public static void clearToken(Context context) {
        getPreferences(context)
                .edit()
                .remove(KEY_ACCESS_TOKEN)
                .apply();
    }
}
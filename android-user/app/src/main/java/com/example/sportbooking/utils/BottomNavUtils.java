package com.example.sportbooking.utils;

import android.app.Activity;
import android.content.Intent;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import com.example.sportbooking.BookingsActivity;
import com.example.sportbooking.CourtSearchActivity;
import com.example.sportbooking.MainActivity;
import com.example.sportbooking.ProfileActivity;
import com.example.sportbooking.R;

public final class BottomNavUtils {

    private BottomNavUtils() {}

    public static void setupBottomNav(Activity activity, int activeTabId) {
        View bottomNav = activity.findViewById(R.id.bottomNav);
        if (bottomNav == null) return;

        View navHome = bottomNav.findViewById(R.id.navHome);
        View navSearch = bottomNav.findViewById(R.id.navSearch);
        View navBookings = bottomNav.findViewById(R.id.navBookings);
        View navProfile = bottomNav.findViewById(R.id.navProfile);

        int greenColor = 0xFF0C8B63; // @color/primary
        int grayColor = 0xFF71829C;  // @color/text_secondary

        setTabState(bottomNav, R.id.ivHomeIcon, R.id.tvHomeText, activeTabId == R.id.navHome, greenColor, grayColor);
        setTabState(bottomNav, R.id.ivSearchIcon, R.id.tvSearchText, activeTabId == R.id.navSearch, greenColor, grayColor);
        setTabState(bottomNav, R.id.ivBookingsIcon, R.id.tvBookingsText, activeTabId == R.id.navBookings, greenColor, grayColor);
        setTabState(bottomNav, R.id.ivProfileIcon, R.id.tvProfileText, activeTabId == R.id.navProfile, greenColor, grayColor);

        if (navHome != null && activeTabId != R.id.navHome) {
            navHome.setOnClickListener(v -> {
                Intent intent = new Intent(activity, MainActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                activity.startActivity(intent);
                activity.finish();
            });
        }

        if (navSearch != null && activeTabId != R.id.navSearch) {
            navSearch.setOnClickListener(v -> {
                Intent intent = new Intent(activity, CourtSearchActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                activity.startActivity(intent);
                activity.finish();
            });
        }

        if (navBookings != null && activeTabId != R.id.navBookings) {
            navBookings.setOnClickListener(v -> {
                Intent intent = new Intent(activity, BookingsActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                activity.startActivity(intent);
                activity.finish();
            });
        }

        if (navProfile != null && activeTabId != R.id.navProfile) {
            navProfile.setOnClickListener(v -> {
                Intent intent = new Intent(activity, ProfileActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                activity.startActivity(intent);
                activity.finish();
            });
        }
    }

    private static void setTabState(View parent, int iconId, int textId, boolean active, int green, int gray) {
        ImageView icon = parent.findViewById(iconId);
        TextView text = parent.findViewById(textId);
        if (icon != null) {
            icon.setColorFilter(active ? green : gray);
        }
        if (text != null) {
            text.setTextColor(active ? green : gray);
            text.getPaint().setFakeBoldText(active);
        }
    }
}

package com.example.sportbooking.utils;

import android.app.Activity;
import android.content.Intent;
import android.view.View;
import android.widget.ImageView;

import com.example.sportbooking.BookingsActivity;
import com.example.sportbooking.CourtSearchActivity;
import com.example.sportbooking.ProfileActivity;
import com.example.sportbooking.R;

public final class BottomNavUtils {

    private BottomNavUtils() {}

    public static void setupBottomNav(Activity activity, int activeTabId) {
        View bottomNav = activity.findViewById(R.id.bottomNav);
        if (bottomNav == null) return;

        View navHome = bottomNav.findViewById(R.id.navHome);
        View navBookings = bottomNav.findViewById(R.id.navBookings);
        View navProfile = bottomNav.findViewById(R.id.navProfile);

        int greenColor = 0xFF0C8B63; // @color/primary
        int grayColor = 0xFF71829C;  // @color/text_secondary

        setTabState(bottomNav, R.id.ivHomeIcon, R.id.tvNavHome, activeTabId == R.id.navHome, greenColor, grayColor);
        setTabState(bottomNav, R.id.ivBookingsIcon, R.id.tvNavBookings, activeTabId == R.id.navBookings, greenColor, grayColor);
        setTabState(bottomNav, R.id.ivProfileIcon, R.id.tvNavProfile, activeTabId == R.id.navProfile, greenColor, grayColor);

        if (navHome != null && activeTabId != R.id.navHome) {
            navHome.setOnClickListener(v -> navigateTab(activity, CourtSearchActivity.class));
        }

        if (navBookings != null && activeTabId != R.id.navBookings) {
            navBookings.setOnClickListener(v -> navigateTab(activity, BookingsActivity.class));
        }

        if (navProfile != null && activeTabId != R.id.navProfile) {
            navProfile.setOnClickListener(v -> navigateTab(activity, ProfileActivity.class));
        }
    }

    private static void navigateTab(Activity activity, Class<?> target) {
        Intent intent = new Intent(activity, target);
        intent.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        activity.startActivity(intent);
    }

    public static void handleBack(Activity activity) {
        if (activity instanceof CourtSearchActivity) {
            activity.finishAffinity();
            return;
        }
        Intent intent = new Intent(activity, CourtSearchActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        activity.startActivity(intent);
    }

    public static void openBookingsAfterBooking(Activity activity) {
        Intent intent = new Intent(activity, BookingsActivity.class);
        intent.putExtra(BookingsActivity.EXTRA_REFRESH_BOOKINGS, true);
        intent.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        activity.startActivity(intent);
    }

    private static void setTabState(View parent, int iconId, int labelId, boolean active, int green, int gray) {
        ImageView icon = parent.findViewById(iconId);
        if (icon != null) {
            icon.setColorFilter(active ? green : gray);
        }
        View label = parent.findViewById(labelId);
        if (label instanceof android.widget.TextView) {
            ((android.widget.TextView) label).setTextColor(active ? green : gray);
        }
    }
}

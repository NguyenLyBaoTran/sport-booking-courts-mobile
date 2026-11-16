package com.example.sportbooking.utils;

import android.app.Activity;
import android.content.Intent;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import com.example.sportbooking.MainActivity;
import com.example.sportbooking.R;

public final class BottomNavUtils {
    private BottomNavUtils() {}

    public static void setupBottomNav(MainActivity activity, int activeTabId) {
        View nav = activity.findViewById(R.id.bottomNav);
        if (nav == null) return;
        setTabState(nav, R.id.ivHomeIcon, R.id.tvNavHome, activeTabId == R.id.navHome);
        setTabState(nav, R.id.ivBookingsIcon, R.id.tvNavBookings, activeTabId == R.id.navBookings);
        setTabState(nav, R.id.ivProfileIcon, R.id.tvNavProfile, activeTabId == R.id.navProfile);
        nav.findViewById(R.id.navHome).setOnClickListener(v -> activity.selectTab(R.id.navHome));
        nav.findViewById(R.id.navBookings).setOnClickListener(v -> activity.selectTab(R.id.navBookings));
        nav.findViewById(R.id.navProfile).setOnClickListener(v -> activity.selectTab(R.id.navProfile));
    }

    private static void setTabState(View parent, int iconId, int labelId, boolean active) {
        int color = active ? 0xFF0C8B63 : 0xFF71829C;
        ImageView icon = parent.findViewById(iconId);
        TextView label = parent.findViewById(labelId);
        if (icon != null) icon.setColorFilter(color);
        if (label != null) label.setTextColor(color);
    }

    public static void openBookingsAfterBooking(Activity activity) {
        Intent intent = new Intent(activity, MainActivity.class);
        intent.putExtra(MainActivity.EXTRA_OPEN_HISTORY, true);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        activity.startActivity(intent);
    }
}

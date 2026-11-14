package com.example.sportbooking;

import android.app.DatePickerDialog;
import android.content.Intent;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.repository.CourtRepository;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;

import java.math.BigDecimal;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;

public class SelectDateTimeActivity extends AppCompatActivity {

    private int courtId;
    private String courtName;

    private CourtRepository courtRepository;
    private BookingRepository bookingRepository;

    private LinearLayout layoutDateContainer;
    private RecyclerView rvTimeSlots;
    private ProgressBar progressBar;
    private TextView tvEmptySlots;
    private TextView tvSelectionSummary;
    private Button btnProceedToBook;

    private final List<JsonObject> slotList = new ArrayList<>();
    private TimeSlotAdapter slotAdapter;
    private String selectedDateStr = "";
    private final List<JsonObject> selectedSlots = new ArrayList<>();
    private int quoteRequestVersion = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_select_date_time);

        courtId = getIntent().getIntExtra("court_id", -1);
        courtName = getIntent().getStringExtra("court_name");

        courtRepository = new CourtRepository(this);
        bookingRepository = new BookingRepository(this);

        layoutDateContainer = findViewById(R.id.layoutDateContainer);
        rvTimeSlots = findViewById(R.id.rvTimeSlots);
        progressBar = findViewById(R.id.progressBar);
        tvEmptySlots = findViewById(R.id.tvEmptySlots);
        tvSelectionSummary = findViewById(R.id.tvSelectionSummary);
        btnProceedToBook = findViewById(R.id.btnProceedToBook);

        findViewById(R.id.ivBack).setOnClickListener(v -> finish());
        findViewById(R.id.btnPickCalendar).setOnClickListener(v -> showFullCalendar());

        rvTimeSlots.setLayoutManager(new GridLayoutManager(this, 4));
        slotAdapter = new TimeSlotAdapter(slotList, this::toggleSlotSelection);
        rvTimeSlots.setAdapter(slotAdapter);

        setupDateCards();
        btnProceedToBook.setOnClickListener(v -> bookSelectedSlot());
    }

    private void showFullCalendar() {
        Calendar c = Calendar.getInstance();
        new DatePickerDialog(this, (view, year, month, dayOfMonth) -> {
            Calendar chosen = Calendar.getInstance();
            chosen.set(year, month, dayOfMonth);
            SimpleDateFormat fullFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
            String pickedDate = fullFormat.format(chosen.getTime());
            selectedDateStr = pickedDate;
            loadTimeSlots(pickedDate);
        }, c.get(Calendar.YEAR), c.get(Calendar.MONTH), c.get(Calendar.DAY_OF_MONTH)).show();
    }

    private void setupDateCards() {
        layoutDateContainer.removeAllViews();
        SimpleDateFormat dayFormat = new SimpleDateFormat("EEE", Locale.ENGLISH);
        SimpleDateFormat dateFormat = new SimpleDateFormat("dd", Locale.getDefault());
        SimpleDateFormat fullFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());

        Calendar calendar = Calendar.getInstance();
        final View[] selectedDateCard = {null};

        for (int i = 0; i < 7; i++) {
            Date date = calendar.getTime();
            String dayOfWeek = dayFormat.format(date);
            String dayOfMonth = dateFormat.format(date);
            String fullDate = fullFormat.format(date);

            View cardView = LayoutInflater.from(this).inflate(R.layout.item_date_card, layoutDateContainer, false);
            TextView tvDay = cardView.findViewById(R.id.tvDayName);
            TextView tvDate = cardView.findViewById(R.id.tvDateNumber);

            tvDay.setText(dayOfWeek);
            tvDate.setText(dayOfMonth);

            if (i == 0) {
                selectedDateStr = fullDate;
                cardView.setSelected(true);
                cardView.setBackgroundResource(R.drawable.bg_primary_radius);
                tvDay.setTextColor(0xFFFFFFFF);
                tvDate.setTextColor(0xFFFFFFFF);
                selectedDateCard[0] = cardView;
                loadTimeSlots(fullDate);
            }

            cardView.setOnClickListener(v -> {
                if (selectedDateCard[0] != null) {
                    selectedDateCard[0].setSelected(false);
                    selectedDateCard[0].setBackgroundResource(R.drawable.bg_card);
                    TextView prevDay = selectedDateCard[0].findViewById(R.id.tvDayName);
                    TextView prevDate = selectedDateCard[0].findViewById(R.id.tvDateNumber);
                    prevDay.setTextColor(0xFF71829C);
                    prevDate.setTextColor(0xFF263449);
                }

                cardView.setSelected(true);
                cardView.setBackgroundResource(R.drawable.bg_primary_radius);
                tvDay.setTextColor(0xFFFFFFFF);
                tvDate.setTextColor(0xFFFFFFFF);
                selectedDateCard[0] = cardView;

                selectedDateStr = fullDate;
                loadTimeSlots(fullDate);
            });

            layoutDateContainer.addView(cardView);
            calendar.add(Calendar.DAY_OF_YEAR, 1);
        }
    }

    private void loadTimeSlots(String date) {
        progressBar.setVisibility(View.VISIBLE);
        tvEmptySlots.setVisibility(View.GONE);
        slotList.clear();
        slotAdapter.notifyDataSetChanged();
        selectedSlots.clear();
        slotAdapter.setSelectedIds(new ArrayList<>());
        quoteRequestVersion++;
        updateSelectionSummary(null);
        btnProceedToBook.setEnabled(false);

        courtRepository.getTimeSlots(courtId, date, new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    JsonObject slot = result.get(i).getAsJsonObject();
                    if (slot.has("is_active") && !slot.get("is_active").isJsonNull()
                            && slot.get("is_active").getAsBoolean()) {
                        slotList.add(slot);
                    }
                }
                slotAdapter.notifyDataSetChanged();
                tvEmptySlots.setVisibility(slotList.isEmpty() ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                slotAdapter.notifyDataSetChanged();
                tvEmptySlots.setText(error);
                tvEmptySlots.setVisibility(View.VISIBLE);
            }
        });
    }

    private void bookSelectedSlot() {
        if (selectedSlots.isEmpty()) {
            return;
        }

        btnProceedToBook.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);
        List<Integer> selectedIds = selectedSlotIds();
        bookingRepository.getBookingQuote(selectedIds, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                progressBar.setVisibility(View.GONE);
                String totalAmount = getValidQuoteAmount(result);
                if (totalAmount == null) {
                    btnProceedToBook.setEnabled(false);
                    Toast.makeText(
                            SelectDateTimeActivity.this,
                            "The booking quote did not include a valid price. Please try again.",
                            Toast.LENGTH_LONG
                    ).show();
                    return;
                }

                Intent intent = new Intent(SelectDateTimeActivity.this, PaymentActivity.class);
                intent.putExtra("time_slot_ids", toIntArray(selectedIds));
                intent.putExtra("total_amount", totalAmount);
                intent.putExtra("court_name", courtName != null ? courtName : "Court #" + courtId);
                intent.putExtra("date", selectedDateStr);
                intent.putExtra("time_slot", formatTime(result.get("start_time").getAsString()) + " - "
                        + formatTime(result.get("end_time").getAsString()));
                intent.putExtra("duration_minutes", result.has("duration_minutes")
                        ? result.get("duration_minutes").getAsInt() : 0);
                startActivity(intent);
                finish();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                btnProceedToBook.setEnabled(false);
                Toast.makeText(SelectDateTimeActivity.this, error, Toast.LENGTH_LONG).show();
                loadTimeSlots(selectedDateStr);
            }
        });
    }

    private void toggleSlotSelection(JsonObject slot) {
        if (!isSelectable(slot)) {
            Toast.makeText(this, "This slot is unavailable.", Toast.LENGTH_SHORT).show();
            return;
        }
        int id = slot.get("id").getAsInt();
        List<JsonObject> candidate = new ArrayList<>(selectedSlots);
        int existing = -1;
        for (int i = 0; i < candidate.size(); i++) {
            if (candidate.get(i).get("id").getAsInt() == id) existing = i;
        }
        if (existing >= 0) candidate.remove(existing); else candidate.add(slot);
        candidate.sort(Comparator.comparing(item -> item.get("start_time").getAsString()));
        if (existing < 0 && !isConsecutive(candidate)) {
            Toast.makeText(this, "Select only consecutive slots on this court and date.", Toast.LENGTH_LONG).show();
            return;
        }
        selectedSlots.clear();
        selectedSlots.addAll(candidate);
        slotAdapter.setSelectedIds(selectedSlotIds());
        boolean quoteable = !selectedSlots.isEmpty() && isConsecutive(selectedSlots);
        btnProceedToBook.setEnabled(false);
        updateSelectionSummary(selectedSlots.isEmpty() ? null : (quoteable ? null : "Selection has a gap. Select the missing slot or remove another selection."));
        quoteRequestVersion++;
        if (!quoteable) return;
        int request = quoteRequestVersion;
        bookingRepository.getBookingQuote(selectedSlotIds(), new ApiCallback<JsonObject>() {
            @Override public void onSuccess(JsonObject quote) {
                if (request != quoteRequestVersion || selectedSlots.isEmpty()) return;
                String amount = getValidQuoteAmount(quote);
                if (amount == null) {
                    updateSelectionSummary("Price quote unavailable. Try again before proceeding.");
                    return;
                }
                int minutes = quote.has("duration_minutes") ? quote.get("duration_minutes").getAsInt() : 0;
                updateSelectionSummary(selectedSlots.size() + " slot(s) · " + (minutes / 60.0) + " hours · " + formatPrice(amount));
                btnProceedToBook.setEnabled(true);
            }
            @Override public void onError(String error) {
                if (request == quoteRequestVersion) {
                    Toast.makeText(SelectDateTimeActivity.this, "Availability changed. Slots have been refreshed.", Toast.LENGTH_LONG).show();
                    loadTimeSlots(selectedDateStr);
                }
            }
        });
    }

    private boolean isConsecutive(List<JsonObject> slots) {
        return areContiguous(slots, courtId, selectedDateStr);
    }

    static boolean areContiguous(List<JsonObject> slots, int courtId, String selectedDate) {
        if (slots.isEmpty()) return true;
        Set<Integer> uniqueIds = new HashSet<>();
        for (int i = 0; i < slots.size(); i++) {
            JsonObject slot = slots.get(i);
            if (!isSelectable(slot) || slot.get("court_id").getAsInt() != courtId
                    || !selectedDate.equals(slot.get("slot_date").getAsString())
                    || !uniqueIds.add(slot.get("id").getAsInt())) return false;
            if (i > 0 && !slots.get(i - 1).get("end_time").getAsString()
                    .equals(slot.get("start_time").getAsString())) return false;
        }
        return true;
    }

    static boolean isSelectable(JsonObject slot) {
        return slot.has("id") && slot.has("is_active") && slot.get("is_active").getAsBoolean()
                && slot.has("is_selectable") && slot.get("is_selectable").getAsBoolean()
                && slot.has("reservation_status") && "AVAILABLE".equalsIgnoreCase(slot.get("reservation_status").getAsString());
    }

    private List<Integer> selectedSlotIds() {
        List<Integer> ids = new ArrayList<>();
        for (JsonObject slot : selectedSlots) ids.add(slot.get("id").getAsInt());
        return ids;
    }

    private static int[] toIntArray(List<Integer> values) {
        int[] result = new int[values.size()];
        for (int i = 0; i < values.size(); i++) result[i] = values.get(i);
        return result;
    }

    private void updateSelectionSummary(String message) {
        if (message != null) {
            tvSelectionSummary.setText(message);
        } else if (selectedSlots.isEmpty()) {
            tvSelectionSummary.setText("Choose one or more consecutive available slots.");
        } else {
            tvSelectionSummary.setText(selectedSlots.size() + " slot(s) selected · loading price quote…");
        }
    }

    private static String formatPrice(String raw) {
        try {
            return java.text.NumberFormat.getInstance(Locale.getDefault()).format(new java.math.BigDecimal(raw)) + " VND";
        } catch (Exception ignored) { return "Price unavailable"; }
    }

    static String formatTime(String value) {
        return value != null && value.length() >= 5 ? value.substring(0, 5) : value;
    }

    private String getValidQuoteAmount(JsonObject quote) {
        if (quote == null || !quote.has("total_amount")) {
            return null;
        }
        JsonElement amountElement = quote.get("total_amount");
        if (amountElement == null || amountElement.isJsonNull() || !amountElement.isJsonPrimitive()) {
            return null;
        }
        JsonPrimitive amountPrimitive = amountElement.getAsJsonPrimitive();
        if (!amountPrimitive.isNumber() && !amountPrimitive.isString()) {
            return null;
        }
        try {
            BigDecimal amount = new BigDecimal(amountPrimitive.getAsString());
            if (amount.signum() <= 0 || amount.scale() > 2) {
                return null;
            }
            return amountPrimitive.getAsString();
        } catch (NumberFormatException error) {
            return null;
        }
    }

    public static class TimeSlotAdapter extends RecyclerView.Adapter<TimeSlotAdapter.ViewHolder> {
        private final List<JsonObject> items;
        private final OnSlotClickListener listener;
        private final Set<Integer> selectedIds = new HashSet<>();

        public interface OnSlotClickListener {
            void onSlotClick(JsonObject slot);
        }

        public TimeSlotAdapter(List<JsonObject> items, OnSlotClickListener listener) {
            this.items = items;
            this.listener = listener;
        }

        public void setSelectedIds(List<Integer> ids) {
            selectedIds.clear();
            selectedIds.addAll(ids);
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_time_slot, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            JsonObject slot = items.get(position);
            String startTime = slot.has("start_time") ? formatTime(slot.get("start_time").getAsString()) : "--:--";
            String endTime = slot.has("end_time") ? formatTime(slot.get("end_time").getAsString()) : "--:--";
            String state = slot.has("reservation_status") ? slot.get("reservation_status").getAsString() : "UNAVAILABLE";
            if (!slot.has("is_selectable") || !slot.get("is_selectable").getAsBoolean()) {
                if ("AVAILABLE".equalsIgnoreCase(state)) state = "UNAVAILABLE";
            }
            holder.tvTime.setText(startTime + " - " + endTime + "\n" + state);

            int id = slot.has("id") ? slot.get("id").getAsInt() : -1;
            boolean isSelected = selectedIds.contains(id);
            boolean selectable = slot.has("is_selectable") && slot.get("is_selectable").getAsBoolean();
            holder.itemView.setSelected(isSelected);
            if (isSelected) {
                holder.itemView.setBackground(slotBackground(0xFF0C8B63, holder.itemView));
                holder.tvTime.setTextColor(0xFFFFFFFF);
            } else {
                holder.itemView.setBackground(slotBackground(slotStateColor(state), holder.itemView));
                holder.tvTime.setTextColor(slotStateTextColor(state));
            }
            holder.itemView.setAlpha(selectable || isSelected ? 1f : 0.72f);
            holder.itemView.setEnabled(selectable || isSelected);

            holder.itemView.setOnClickListener(v -> {
                if (!selectable && !isSelected) return;
                listener.onSlotClick(slot);
            });
        }

        private GradientDrawable slotBackground(int color, View view) {
            GradientDrawable background = new GradientDrawable();
            background.setColor(color);
            background.setCornerRadius(10 * view.getResources().getDisplayMetrics().density);
            return background;
        }

        private int slotStateColor(String state) {
            if ("AVAILABLE".equalsIgnoreCase(state)) return 0xFFE7F5EF;
            if ("HELD".equalsIgnoreCase(state)) return 0xFFFFF2D8;
            if ("BOOKED".equalsIgnoreCase(state)) return 0xFFFCE8E6;
            return 0xFFE9EDF2;
        }

        private int slotStateTextColor(String state) {
            if ("AVAILABLE".equalsIgnoreCase(state)) return 0xFF176B4D;
            if ("HELD".equalsIgnoreCase(state)) return 0xFF895500;
            if ("BOOKED".equalsIgnoreCase(state)) return 0xFF8C3A32;
            return 0xFF71829C;
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            TextView tvTime;
            ViewHolder(View itemView) {
                super(itemView);
                tvTime = itemView.findViewById(R.id.tvSlotTime);
            }
        }
    }
}

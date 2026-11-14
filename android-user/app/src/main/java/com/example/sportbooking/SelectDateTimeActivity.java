package com.example.sportbooking;

import android.app.DatePickerDialog;
import android.content.Intent;
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

public class SelectDateTimeActivity extends AppCompatActivity {

    private int courtId;
    private String courtName;

    private CourtRepository courtRepository;
    private BookingRepository bookingRepository;

    private LinearLayout layoutDateContainer;
    private RecyclerView rvTimeSlots;
    private ProgressBar progressBar;
    private TextView tvEmptySlots;
    private Button btnProceedToBook;

    private final List<JsonObject> slotList = new ArrayList<>();
    private TimeSlotAdapter slotAdapter;
    private Integer selectedTimeSlotId = null;
    private String selectedDateStr = "";
    private JsonObject selectedSlot;

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
        btnProceedToBook = findViewById(R.id.btnProceedToBook);

        findViewById(R.id.ivBack).setOnClickListener(v -> finish());
        findViewById(R.id.btnPickCalendar).setOnClickListener(v -> showFullCalendar());

        rvTimeSlots.setLayoutManager(new GridLayoutManager(this, 4));
        slotAdapter = new TimeSlotAdapter(slotList, slot -> {
            selectedTimeSlotId = slot.has("id") && !slot.get("id").isJsonNull()
                    ? slot.get("id").getAsInt() : null;
            selectedSlot = slot;
            btnProceedToBook.setEnabled(selectedTimeSlotId != null && selectedTimeSlotId > 0);
        });
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
        selectedTimeSlotId = null;
        selectedSlot = null;
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
        if (selectedTimeSlotId == null) {
            return;
        }

        btnProceedToBook.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);
        bookingRepository.getBookingQuote(selectedTimeSlotId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                progressBar.setVisibility(View.GONE);
                String totalAmount = getValidQuoteAmount(result);
                if (totalAmount == null) {
                    btnProceedToBook.setEnabled(true);
                    Toast.makeText(
                            SelectDateTimeActivity.this,
                            "The booking quote did not include a valid price. Please try again.",
                            Toast.LENGTH_LONG
                    ).show();
                    return;
                }

                Intent intent = new Intent(SelectDateTimeActivity.this, PaymentActivity.class);
                intent.putExtra("time_slot_id", selectedTimeSlotId);
                intent.putExtra("total_amount", totalAmount);
                intent.putExtra("court_name", courtName != null ? courtName : "Badminton Court 1");
                intent.putExtra("date", selectedDateStr);
                startActivity(intent);
                finish();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                btnProceedToBook.setEnabled(true);
                Toast.makeText(SelectDateTimeActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
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
            if (amount.signum() < 0 || amount.scale() > 2) {
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
        private int selectedPosition = -1;

        public interface OnSlotClickListener {
            void onSlotClick(JsonObject slot);
        }

        public TimeSlotAdapter(List<JsonObject> items, OnSlotClickListener listener) {
            this.items = items;
            this.listener = listener;
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
            String startTime = slot.has("start_time") ? slot.get("start_time").getAsString() : "08:00";
            holder.tvTime.setText(startTime);

            boolean isSelected = (position == selectedPosition);
            holder.itemView.setSelected(isSelected);
            if (isSelected) {
                holder.itemView.setBackgroundResource(R.drawable.bg_primary_radius);
                holder.tvTime.setTextColor(0xFFFFFFFF);
            } else {
                holder.itemView.setBackgroundResource(R.drawable.bg_card);
                holder.tvTime.setTextColor(0xFF263449);
            }

            holder.itemView.setOnClickListener(v -> {
                int oldPos = selectedPosition;
                selectedPosition = holder.getAbsoluteAdapterPosition();
                if (oldPos != -1) notifyItemChanged(oldPos);
                notifyItemChanged(selectedPosition);
                listener.onSlotClick(slot);
            });
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

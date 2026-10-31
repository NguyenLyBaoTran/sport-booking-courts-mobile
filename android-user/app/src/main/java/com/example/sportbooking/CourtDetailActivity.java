package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.BookingRepository;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.utils.SportImageMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.text.ParseException;

public class CourtDetailActivity extends AppCompatActivity {

    private int courtId;
    private String courtName, courtDesc;

    private CourtRepository courtRepository;
    private BookingRepository bookingRepository;

    private TextView tvName, tvDesc, tvDetailPrice, tvEmptySlots;
    private ImageView ivHero, ivPhoto1, ivPhoto2, ivPhoto3;
    private EditText etDate;
    private Button btnLoadSlots, btnBook;
    private ProgressBar progressBar;
    private RecyclerView rvTimeSlots;

    private final List<JsonObject> slotList = new ArrayList<>();
    private TimeSlotAdapter slotAdapter;
    private Integer selectedTimeSlotId = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_court_detail);

        courtId = getIntent().getIntExtra("court_id", -1);
        courtName = getIntent().getStringExtra("court_name");
        courtDesc = getIntent().getStringExtra("court_desc");

        courtRepository = new CourtRepository(this);
        bookingRepository = new BookingRepository(this);

        tvName = findViewById(R.id.tvDetailName);
        tvDesc = findViewById(R.id.tvDetailDescription);
        tvDetailPrice = findViewById(R.id.tvDetailPrice);
        tvEmptySlots = findViewById(R.id.tvEmptySlots);
        ivHero = findViewById(R.id.ivDetailHero);
        ivPhoto1 = findViewById(R.id.ivDetailPhoto1);
        ivPhoto2 = findViewById(R.id.ivDetailPhoto2);
        ivPhoto3 = findViewById(R.id.ivDetailPhoto3);
        etDate = findViewById(R.id.etDate);
        btnLoadSlots = findViewById(R.id.btnLoadSlots);
        btnBook = findViewById(R.id.btnBook);
        progressBar = findViewById(R.id.progressBar);
        rvTimeSlots = findViewById(R.id.rvTimeSlots);
        findViewById(R.id.ivBack).setOnClickListener(v -> finish());

        tvName.setText(courtName != null ? courtName : "Court Details");
        tvDesc.setText(courtDesc != null ? courtDesc : "");
        JsonObject initialCourt = new JsonObject();
        if (getIntent().hasExtra("sport_id")) {
            initialCourt.addProperty("sport_id", getIntent().getIntExtra("sport_id", 0));
        }
        if (courtName != null) {
            initialCourt.addProperty("name", courtName);
        }
        int primaryImage = SportImageMapper.getPrimaryImage(initialCourt);
        ivHero.setImageResource(primaryImage);
        ivPhoto1.setImageResource(primaryImage);
        ivPhoto2.setImageResource(SportImageMapper.getSecondaryImage(initialCourt, courtName));
        ivPhoto3.setImageResource(primaryImage);

        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(new Date());
        etDate.setText(today);

        rvTimeSlots.setLayoutManager(new LinearLayoutManager(this));
        slotAdapter = new TimeSlotAdapter(slotList, slot -> {
            selectedTimeSlotId = slot.has("id") ? slot.get("id").getAsInt() : null;
            btnBook.setEnabled(selectedTimeSlotId != null);
        });
        rvTimeSlots.setAdapter(slotAdapter);

        btnLoadSlots.setOnClickListener(v -> loadTimeSlots());
        btnBook.setOnClickListener(v -> bookSelectedSlot());

        loadCourtDetail();
        loadTimeSlots();
    }

    private void loadCourtDetail() {
        if (courtId <= 0) {
            Toast.makeText(this, "Invalid court ID", Toast.LENGTH_SHORT).show();
            return;
        }

        courtRepository.getCourt(courtId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject court) {
                String name = court.has("name") && !court.get("name").isJsonNull()
                        ? court.get("name").getAsString() : courtName;
                String description = court.has("description") && !court.get("description").isJsonNull()
                        ? court.get("description").getAsString() : "";
                tvName.setText(name != null ? name : "Court Details");
                tvDesc.setText(description);
                String price = court.has("price_per_hour") && !court.get("price_per_hour").isJsonNull()
                        ? court.get("price_per_hour").getAsString() : null;
                tvDetailPrice.setText(price == null || price.trim().isEmpty() ? "N/A" : price + " VND/h");
                int primaryImage = SportImageMapper.getPrimaryImage(court, courtName);
                ivHero.setImageResource(primaryImage);
                ivPhoto1.setImageResource(primaryImage);
                ivPhoto2.setImageResource(SportImageMapper.getSecondaryImage(court, courtName));
                ivPhoto3.setImageResource(primaryImage);
            }

            @Override
            public void onError(String error) {
                Toast.makeText(CourtDetailActivity.this, "Could not refresh court details: " + error, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void loadTimeSlots() {
        String date = etDate.getText().toString().trim();
        if (date.isEmpty()) {
            Toast.makeText(this, "Please enter a date", Toast.LENGTH_SHORT).show();
            return;
        }
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        dateFormat.setLenient(false);
        try {
            dateFormat.parse(date);
        } catch (ParseException e) {
            tvEmptySlots.setText("Please use date format yyyy-MM-dd.");
            tvEmptySlots.setVisibility(View.VISIBLE);
            Toast.makeText(this, "Invalid date format. Use yyyy-MM-dd", Toast.LENGTH_SHORT).show();
            return;
        }

        progressBar.setVisibility(View.VISIBLE);
        tvEmptySlots.setVisibility(View.GONE);
        slotList.clear();
        slotAdapter.notifyDataSetChanged();
        selectedTimeSlotId = null;
        btnBook.setEnabled(false);

        courtRepository.getTimeSlots(courtId, date, new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    JsonObject slot = result.get(i).getAsJsonObject();
                    boolean active = !slot.has("is_active")
                            || slot.get("is_active").isJsonPrimitive()
                            && slot.get("is_active").getAsBoolean();
                    if (active && slot.has("id") && slot.has("court_id")
                            && slot.get("court_id").getAsInt() == courtId) {
                        slotList.add(slot);
                    }
                }
                if (slotList.isEmpty()) {
                    tvEmptySlots.setText("No available time slots for this date.");
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

        btnBook.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);

        bookingRepository.createBooking(selectedTimeSlotId, new ApiCallback<JsonObject>() {
            @Override
            public void onSuccess(JsonObject result) {
                progressBar.setVisibility(View.GONE);
                int bookingId = result.has("id") ? result.get("id").getAsInt() : -1;
                String totalAmount = result.has("total_amount") && !result.get("total_amount").isJsonNull()
                        ? result.get("total_amount").getAsString() : "N/A";

                Intent intent = new Intent(CourtDetailActivity.this, PaymentActivity.class);
                intent.putExtra("booking_id", bookingId);
                intent.putExtra("total_amount", totalAmount);
                intent.putExtra("court_name", tvName.getText().toString());
                intent.putExtra("date", etDate.getText().toString());
                startActivity(intent);
                finish();
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                btnBook.setEnabled(true);
                Toast.makeText(CourtDetailActivity.this, error, Toast.LENGTH_LONG).show();
            }
        });
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
            String startTime = slot.has("start_time") ? slot.get("start_time").getAsString() : "00:00";
            String endTime = slot.has("end_time") ? slot.get("end_time").getAsString() : "00:00";
            holder.tvTime.setText(startTime + " - " + endTime);

            holder.itemView.setSelected(position == selectedPosition);
            holder.itemView.setBackgroundColor(position == selectedPosition ? 0xFFE0F2F1 : 0xFFFFFFFF);

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

package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.utils.SportImageMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.util.List;

public class CourtSearchActivity extends AppCompatActivity {

    private CourtRepository courtRepository;
    private Spinner spinnerVenues, spinnerSports;
    private RecyclerView rvCourts;
    private ProgressBar progressBar;
    private TextView tvEmpty;

    private final List<VenueItem> venueList = new ArrayList<>();
    private final List<SportItem> sportList = new ArrayList<>();
    private final List<JsonObject> courtList = new ArrayList<>();
    private CourtAdapter courtAdapter;

    private Integer selectedVenueId = null;
    private Integer selectedSportId = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_court_search);

        courtRepository = new CourtRepository(this);

        spinnerVenues = findViewById(R.id.spinnerVenues);
        spinnerSports = findViewById(R.id.spinnerSports);
        rvCourts = findViewById(R.id.rvCourts);
        progressBar = findViewById(R.id.progressBar);
        tvEmpty = findViewById(R.id.tvEmpty);

        TextView tvTitle = findViewById(R.id.tvTitle);
        String targetSport = getIntent().getStringExtra("sport_name");
        if (tvTitle != null && targetSport != null) {
            tvTitle.setText(targetSport + " Courts");
        }

        findViewById(R.id.ivBack).setOnClickListener(v -> finish());

        rvCourts.setLayoutManager(new LinearLayoutManager(this));
        courtAdapter = new CourtAdapter(courtList, court -> {
            Intent intent = new Intent(this, CourtDetailActivity.class);
            intent.putExtra("court_id", court.get("id").getAsInt());
            intent.putExtra("court_name", court.has("name") ? court.get("name").getAsString() : "Court");
            intent.putExtra("court_desc", court.has("description") && !court.get("description").isJsonNull() ? court.get("description").getAsString() : "");
            if (court.has("sport_id")) {
                intent.putExtra("sport_id", court.get("sport_id").getAsInt());
            }
            startActivity(intent);
        });
        rvCourts.setAdapter(courtAdapter);

        setupSpinners();
        loadFilters();
    }

    private void setupSpinners() {
        spinnerVenues.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                VenueItem item = venueList.get(position);
                selectedVenueId = item.id;
                searchCourts();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        spinnerSports.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                SportItem item = sportList.get(position);
                selectedSportId = item.id;
                searchCourts();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
    }

    private void loadFilters() {
        venueList.clear();
        venueList.add(new VenueItem(null, "All Venues"));
        sportList.clear();
        sportList.add(new SportItem(null, "All Sports"));

        courtRepository.getVenues(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                for (int i = 0; i < result.size(); i++) {
                    JsonObject obj = result.get(i).getAsJsonObject();
                    int id = obj.get("id").getAsInt();
                    String name = obj.has("name") ? obj.get("name").getAsString() : "Venue " + id;
                    venueList.add(new VenueItem(id, name));
                }
                updateVenueSpinner();
            }

            @Override
            public void onError(String error) {
                updateVenueSpinner();
            }
        });

        courtRepository.getSports(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                for (int i = 0; i < result.size(); i++) {
                    JsonObject obj = result.get(i).getAsJsonObject();
                    int id = obj.get("id").getAsInt();
                    String name = obj.has("name") ? obj.get("name").getAsString() : "Sport " + id;
                    sportList.add(new SportItem(id, name));
                }
                updateSportSpinner();
            }

            @Override
            public void onError(String error) {
                updateSportSpinner();
            }
        });

        // Hidden filter spinners do not always emit a selection event on Android,
        // so load courts explicitly instead of relying only on spinner listeners.
        searchCourts();
    }

    private void updateVenueSpinner() {
        List<String> names = new ArrayList<>();
        for (VenueItem item : venueList) {
            names.add(item.name);
        }
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, names);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerVenues.setAdapter(adapter);
    }

    private void updateSportSpinner() {
        List<String> names = new ArrayList<>();
        for (SportItem item : sportList) {
            names.add(item.name);
        }
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, names);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerSports.setAdapter(adapter);

        String targetSport = getIntent().getStringExtra("sport_name");
        if (targetSport != null) {
            for (int i = 0; i < sportList.size(); i++) {
                if (sportList.get(i).name.equalsIgnoreCase(targetSport)) {
                    spinnerSports.setSelection(i);
                    break;
                }
            }
        }
    }

    private void searchCourts() {
        progressBar.setVisibility(View.VISIBLE);
        tvEmpty.setVisibility(View.GONE);
        courtList.clear();
        courtAdapter.notifyDataSetChanged();

        courtRepository.searchCourts(selectedVenueId, selectedSportId, new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    courtList.add(result.get(i).getAsJsonObject());
                }
                if (courtList.isEmpty()) {
                    tvEmpty.setText("No courts available.");
                }
                courtAdapter.notifyDataSetChanged();
                tvEmpty.setVisibility(courtList.isEmpty() ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onError(String error) {
                progressBar.setVisibility(View.GONE);
                courtAdapter.notifyDataSetChanged();
                tvEmpty.setText(error);
                tvEmpty.setVisibility(View.VISIBLE);
                Toast.makeText(
                        CourtSearchActivity.this,
                        error,
                        Toast.LENGTH_LONG
                ).show();
            }
        });
    }

    private JsonObject createMockCourt(int id, String name, String tag, String price, boolean available) {
        JsonObject obj = new JsonObject();
        obj.addProperty("id", id);
        obj.addProperty("name", name);
        obj.addProperty("description", "Indoor • Wooden Floor");
        obj.addProperty("price_per_hour", price);
        obj.addProperty("is_active", available);
        return obj;
    }

    public static class VenueItem {
        public Integer id;
        public String name;
        public VenueItem(Integer id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    public static class SportItem {
        public Integer id;
        public String name;
        public SportItem(Integer id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    public static class CourtAdapter extends RecyclerView.Adapter<CourtAdapter.ViewHolder> {
        private final List<JsonObject> items;
        private final OnCourtClickListener listener;

        public interface OnCourtClickListener {
            void onCourtClick(JsonObject court);
        }

        public CourtAdapter(List<JsonObject> items, OnCourtClickListener listener) {
            this.items = items;
            this.listener = listener;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_court, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            JsonObject court = items.get(position);
            String name = court.has("name") ? court.get("name").getAsString() : "Court";
            String desc = court.has("description") && !court.get("description").isJsonNull() ? court.get("description").getAsString() : "No description";
            boolean active = !court.has("is_active") || court.get("is_active").getAsBoolean();

            holder.tvName.setText(name);
            holder.tvDesc.setText(desc.isEmpty() ? "No description" : desc);
            String statusText = active ? "● Available" : "● Busy";
            holder.tvStatus.setText(statusText);
            holder.tvStatus.setTextColor(active ? 0xFF0C8B63 : 0xFFC62828);
            String price = court.has("price_per_hour") && !court.get("price_per_hour").isJsonNull()
                    ? court.get("price_per_hour").getAsString() : null;
            holder.tvPrice.setText(price == null || price.isEmpty() ? "" : price + " VND/h");
            holder.ivCourtImage.setImageResource(SportImageMapper.getPrimaryImage(court));
            holder.itemView.setOnClickListener(v -> listener.onCourtClick(court));
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        public static class ViewHolder extends RecyclerView.ViewHolder {
            public TextView tvName, tvDesc, tvStatus, tvPrice;
            public ImageView ivCourtImage;
            public ViewHolder(View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tvCourtName);
                tvDesc = itemView.findViewById(R.id.tvCourtDescription);
                tvStatus = itemView.findViewById(R.id.tvCourtStatus);
                tvPrice = itemView.findViewById(R.id.tvCourtPrice);
                ivCourtImage = itemView.findViewById(R.id.ivCourtImage);
            }
        }
    }
}

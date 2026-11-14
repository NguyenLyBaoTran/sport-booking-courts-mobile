package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.utils.BottomNavUtils;
import com.example.sportbooking.utils.SportImageMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class CourtSearchActivity extends AppCompatActivity {

    private CourtRepository courtRepository;
    private Spinner spinnerVenues, spinnerSports;
    private RecyclerView rvCourts;
    private ProgressBar progressBar;
    private TextView tvEmpty;
    private EditText etSearch;

    private final List<VenueItem> venueList = new ArrayList<>();
    private final Map<Integer, VenueItem> venueMap = new HashMap<>();
    private final List<SportItem> sportList = new ArrayList<>();
    private final List<JsonObject> allCourts = new ArrayList<>();
    private final List<JsonObject> courtList = new ArrayList<>();
    private CourtAdapter courtAdapter;
    private int searchRequestId = 0;

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
        etSearch = findViewById(R.id.etSearch);

        TextView tvTitle = findViewById(R.id.tvTitle);
        String targetSport = getIntent().getStringExtra("sport_name");
        if (tvTitle != null) {
            tvTitle.setText(targetSport != null ? targetSport + " Courts" : "Courts Search");
        }

        boolean isFromSportCard = getIntent().getBooleanExtra("from_sport_card", false);
        if (isFromSportCard) {
            int initialSportId = getIntent().getIntExtra("sport_id", -1);
            if (initialSportId > 0) {
                selectedSportId = initialSportId;
            }
        }
        BottomNavUtils.setupBottomNav(this, isFromSportCard ? 0 : R.id.navSearch);

        rvCourts.setLayoutManager(new LinearLayoutManager(this));
        courtAdapter = new CourtAdapter(courtList, venueMap, court -> {
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

        if (etSearch != null) {
            etSearch.addTextChangedListener(new TextWatcher() {
                @Override
                public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

                @Override
                public void onTextChanged(CharSequence s, int start, int before, int count) {
                    filterCourts(s.toString());
                }

                @Override
                public void afterTextChanged(Editable s) {}
            });
        }

        setupSpinners();
        loadFilters();
    }

    private void filterCourts(String query) {
        courtList.clear();
        String q = query.toLowerCase().trim();
        for (JsonObject court : allCourts) {
            int venueId = court.has("venue_id") && !court.get("venue_id").isJsonNull()
                    ? court.get("venue_id").getAsInt() : -1;
            int sportId = court.has("sport_id") && !court.get("sport_id").isJsonNull()
                    ? court.get("sport_id").getAsInt() : -1;
            if (selectedVenueId != null && venueId != selectedVenueId) {
                continue;
            }
            if (selectedSportId != null && sportId != selectedSportId) {
                continue;
            }

            String name = court.has("name") && !court.get("name").isJsonNull()
                    ? court.get("name").getAsString().toLowerCase() : "";
            String desc = court.has("description") && !court.get("description").isJsonNull()
                    ? court.get("description").getAsString().toLowerCase() : "";
            String venueInfo = "";
            VenueItem venue = venueMap.get(venueId);
            if (venue != null) {
                venueInfo = (venue.name + " " + venue.address).toLowerCase();
            }

            if (q.isEmpty() || name.contains(q) || desc.contains(q) || venueInfo.contains(q)) {
                courtList.add(court);
            }
        }
        courtAdapter.notifyDataSetChanged();
        tvEmpty.setVisibility(courtList.isEmpty() ? View.VISIBLE : View.GONE);
    }

    private void setupSpinners() {
        spinnerVenues.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (position <= 0 || position >= venueList.size()) {
                    selectedVenueId = null;
                } else {
                    selectedVenueId = venueList.get(position).id;
                }
                filterCourts(etSearch != null ? etSearch.getText().toString() : "");
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
                selectedVenueId = null;
            }
        });

        spinnerSports.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (position <= 0 || position >= sportList.size()) {
                    selectedSportId = null;
                } else {
                    selectedSportId = sportList.get(position).id;
                }
                filterCourts(etSearch != null ? etSearch.getText().toString() : "");
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
                selectedSportId = null;
            }
        });
    }

    private void loadFilters() {
        venueList.clear();
        venueList.add(new VenueItem(null, "All Venues", ""));
        sportList.clear();
        sportList.add(new SportItem(null, "All Sports"));

        courtRepository.getVenues(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                venueMap.clear();
                for (int i = 0; i < result.size(); i++) {
                    JsonObject obj = result.get(i).getAsJsonObject();
                    int id = obj.get("id").getAsInt();
                    String name = obj.has("name") ? obj.get("name").getAsString() : "Venue " + id;
                    String address = obj.has("address") && !obj.get("address").isJsonNull() ? obj.get("address").getAsString() : "";
                    VenueItem item = new VenueItem(id, name, address);
                    venueList.add(item);
                    venueMap.put(id, item);
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

        applyInitialSportFilter();
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
        applyInitialSportFilter();
    }

    private void applyInitialSportFilter() {
        boolean isFromSportCard = getIntent().getBooleanExtra("from_sport_card", false);
        if (!isFromSportCard) {
            selectedSportId = null;
            selectedVenueId = null;
            searchCourts();
            return;
        }

        String targetSport = getIntent().getStringExtra("sport_name");
        int targetSportId = getIntent().getIntExtra("sport_id", -1);
        if (sportList.isEmpty()) {
            searchCourts();
            return;
        }

        if (targetSportId > 0) {
            for (int i = 0; i < sportList.size(); i++) {
                SportItem item = sportList.get(i);
                if (item.id != null && item.id == targetSportId) {
                    selectedSportId = item.id;
                    spinnerSports.setSelection(i);
                    searchCourts();
                    return;
                }
            }
        }

        if (targetSport == null) {
            searchCourts();
            return;
        }

        for (int i = 0; i < sportList.size(); i++) {
            SportItem item = sportList.get(i);
            if (targetSport.equalsIgnoreCase(item.name)) {
                selectedSportId = item.id;
                spinnerSports.setSelection(i);
                searchCourts();
                return;
            }
        }

        searchCourts();
    }

    private void searchCourts() {
        int requestId = ++searchRequestId;
        progressBar.setVisibility(View.VISIBLE);
        tvEmpty.setVisibility(View.GONE);
        allCourts.clear();
        courtList.clear();
        courtAdapter.notifyDataSetChanged();

        courtRepository.searchCourts(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                if (requestId != searchRequestId) {
                    return;
                }
                progressBar.setVisibility(View.GONE);
                for (int i = 0; i < result.size(); i++) {
                    allCourts.add(result.get(i).getAsJsonObject());
                }
                filterCourts(etSearch != null ? etSearch.getText().toString() : "");
            }

            @Override
            public void onError(String error) {
                if (requestId != searchRequestId) {
                    return;
                }
                progressBar.setVisibility(View.GONE);
                allCourts.clear();
                courtList.clear();
                courtAdapter.notifyDataSetChanged();
                tvEmpty.setText(error);
                tvEmpty.setVisibility(View.VISIBLE);
            }
        });
    }

    public static class VenueItem {
        public Integer id;
        public String name;
        public String address;
        public VenueItem(Integer id, String name, String address) {
            this.id = id;
            this.name = name;
            this.address = address;
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
        private final Map<Integer, VenueItem> venueMap;
        private final OnCourtClickListener listener;

        public interface OnCourtClickListener {
            void onCourtClick(JsonObject court);
        }

        public CourtAdapter(List<JsonObject> items, Map<Integer, VenueItem> venueMap, OnCourtClickListener listener) {
            this.items = items;
            this.venueMap = venueMap;
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
            String desc = court.has("description") && !court.get("description").isJsonNull() ? court.get("description").getAsString() : "";
            boolean active = !court.has("is_active") || court.get("is_active").getAsBoolean();

            holder.tvName.setText(name);

            if (court.has("venue_id") && !court.get("venue_id").isJsonNull()) {
                int venueId = court.get("venue_id").getAsInt();
                VenueItem venue = venueMap.get(venueId);
                if (venue != null && venue.name != null) {
                    String loc = venue.name + (!TextUtils.isEmpty(venue.address) ? " • " + venue.address : "");
                    holder.tvLocation.setText(loc);
                    holder.tvLocation.setVisibility(View.VISIBLE);
                } else {
                    holder.tvLocation.setVisibility(View.GONE);
                }
            } else {
                holder.tvLocation.setVisibility(View.GONE);
            }

            if (!desc.trim().isEmpty()) {
                holder.tvDesc.setText(desc);
                holder.tvDesc.setVisibility(View.VISIBLE);
            } else {
                holder.tvDesc.setVisibility(View.GONE);
            }

            String statusText = active ? "● Active" : "● Inactive";
            holder.tvStatus.setText(statusText);
            holder.tvStatus.setTextColor(active ? 0xFF0C8B63 : 0xFFC62828);
            holder.tvStatus.setBackgroundResource(active
                    ? R.drawable.bg_status_available
                    : R.drawable.bg_status_inactive);

            String rawPrice = court.has("price_per_hour") && !court.get("price_per_hour").isJsonNull()
                    ? court.get("price_per_hour").getAsString() : null;
            holder.tvPrice.setText(formatPrice(rawPrice));

            holder.ivCourtImage.setImageResource(SportImageMapper.getPrimaryImage(court));
            holder.itemView.setOnClickListener(v -> listener.onCourtClick(court));
        }

        private String formatPrice(String raw) {
            if (raw == null || raw.trim().isEmpty()) return "";
            try {
                double val = Double.parseDouble(raw);
                NumberFormat nf = NumberFormat.getInstance(Locale.getDefault());
                return nf.format(val) + " VND/h";
            } catch (Exception e) {
                return raw + " VND/h";
            }
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        public static class ViewHolder extends RecyclerView.ViewHolder {
            public TextView tvName, tvLocation, tvDesc, tvStatus, tvPrice;
            public ImageView ivCourtImage;

            public ViewHolder(View itemView) {
                super(itemView);
                tvName = itemView.findViewById(R.id.tvCourtName);
                tvLocation = itemView.findViewById(R.id.tvCourtLocation);
                tvDesc = itemView.findViewById(R.id.tvCourtDescription);
                tvStatus = itemView.findViewById(R.id.tvCourtStatus);
                tvPrice = itemView.findViewById(R.id.tvCourtPrice);
                ivCourtImage = itemView.findViewById(R.id.ivCourtImage);
            }
        }
    }
}

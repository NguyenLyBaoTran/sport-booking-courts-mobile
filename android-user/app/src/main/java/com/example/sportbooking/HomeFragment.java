package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import com.google.android.material.chip.Chip;
import com.google.android.material.chip.ChipGroup;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.CourtRepository;
import com.example.sportbooking.utils.CustomerUiUtils;
import com.example.sportbooking.utils.SportImageMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class HomeFragment extends Fragment {

    private CourtRepository courtRepository;
    private ChipGroup chipSports;
    private ChipGroup chipLocations;
    private RecyclerView rvCourts;
    private ProgressBar progressBar;
    private TextView tvEmpty;
    private EditText etSearch;
    private int filterListsLoaded;

    private final Map<Integer, VenueItem> venueMap = new LinkedHashMap<>();
    private final Map<String, String> availableLocations = new LinkedHashMap<>();
    private final List<SportItem> sportList = new ArrayList<>();
    private final List<JsonObject> allCourts = new ArrayList<>();
    private final List<JsonObject> courtList = new ArrayList<>();
    private CourtAdapter courtAdapter;
    private int searchRequestId = 0;

    private Integer selectedSportId = null;
    private String selectedAddress = "";

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View root = inflater.inflate(R.layout.activity_court_search, container, false);

        courtRepository = new CourtRepository(requireContext());

        chipSports = root.findViewById(R.id.chipSports);
        chipLocations = root.findViewById(R.id.chipLocations);
        rvCourts = root.findViewById(R.id.rvCourts);
        progressBar = root.findViewById(R.id.progressBar);
        tvEmpty = root.findViewById(R.id.tvEmpty);
        etSearch = root.findViewById(R.id.etSearch);

        TextView tvTitle = root.findViewById(R.id.tvTitle);
        if (tvTitle != null) {
            tvTitle.setText("Find a court");
        }
        TextView greeting = root.findViewById(R.id.tvGreeting);
        String savedName = requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE)
                .getString("saved_full_name", "");
        String displayName = savedName == null ? "" : savedName.trim();
        if (greeting != null) greeting.setText(displayName.isEmpty() ? "Hello" : "Hello, " + displayName);

        rvCourts.setLayoutManager(new LinearLayoutManager(requireContext()));
        courtAdapter = new CourtAdapter(courtList, venueMap, court -> {
            Intent intent = new Intent(requireContext(), CourtDetailActivity.class);
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

        loadFilters();
        androidx.core.view.ViewCompat.setNestedScrollingEnabled(rvCourts, false);
        return root;
    }

    private void filterCourts(String query) {
        courtList.clear();
        String q = query.toLowerCase().trim();
        for (JsonObject court : allCourts) {
            int venueId = court.has("venue_id") && !court.get("venue_id").isJsonNull()
                    ? court.get("venue_id").getAsInt() : -1;
            int sportId = court.has("sport_id") && !court.get("sport_id").isJsonNull()
                    ? court.get("sport_id").getAsInt() : -1;
            String name = court.has("name") && !court.get("name").isJsonNull()
                    ? court.get("name").getAsString().toLowerCase() : "";
            String desc = court.has("description") && !court.get("description").isJsonNull()
                    ? court.get("description").getAsString().toLowerCase() : "";
            String venueInfo = "";
            VenueItem venue = venueMap.get(venueId);
            if (venue != null) {
                venueInfo = (venue.name + " " + venue.address).toLowerCase();
            }

            String sportName = "";
            for (SportItem item : sportList) {
                if (item.id != null && item.id == sportId) { sportName = item.name.toLowerCase(); break; }
            }
            if (CustomerUiUtils.matchesCourtFilters(q, name, desc, venueInfo, sportName,
                    venueId, null, sportId, selectedSportId)
                    && CustomerUiUtils.matchesAddressFilter(venue == null ? null : venue.address, selectedAddress)) {
                courtList.add(court);
            }
        }
        courtAdapter.notifyDataSetChanged();
        tvEmpty.setVisibility(courtList.isEmpty() ? View.VISIBLE : View.GONE);
    }

    @Override
    public void onResume() {
        super.onResume();
        refreshGreeting();
    }

    public void refreshGreeting() {
        View root = getView();
        if (root == null) return;
        TextView greeting = root.findViewById(R.id.tvGreeting);
        if (greeting == null) return;
        String name = requireContext().getSharedPreferences("user_profile_prefs", android.content.Context.MODE_PRIVATE)
                .getString("saved_full_name", "");
        name = name == null ? "" : name.trim();
        greeting.setText(name.isEmpty() ? "Hello" : "Hello, " + name);
    }

    private void loadFilters() {
        filterListsLoaded = 0;
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
                    venueMap.put(id, item);
                }
                updateLocationChips();
                onFilterListLoaded();
            }

            @Override
            public void onError(String error) {
                updateLocationChips();
                onFilterListLoaded();
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
                onFilterListLoaded();
            }

            @Override
            public void onError(String error) {
                onFilterListLoaded();
            }
        });
    }

    private void onFilterListLoaded() {
        filterListsLoaded += 1;
        if (filterListsLoaded == 2) applyInitialSportFilter();
    }

    private void updateLocationChips() {
        if (chipLocations == null) return;
        availableLocations.clear();
        for (VenueItem venue : venueMap.values()) {
            if (venue.address == null || venue.address.trim().isEmpty() || !hasCourtsForVenue(venue.id)) continue;
            String key = CustomerUiUtils.normalizeAddress(venue.address);
            if (!availableLocations.containsKey(key)) availableLocations.put(key, venue.address.trim());
        }
        if (!selectedAddress.isEmpty() && !availableLocations.containsKey(selectedAddress)) selectedAddress = "";
        chipLocations.removeAllViews();
        addLocationChip("", "All locations");
        for (Map.Entry<String, String> entry : availableLocations.entrySet()) {
            addLocationChip(entry.getKey(), entry.getValue());
        }
    }

    private void addLocationChip(String key, String label) {
        Chip chip = createFilterChip(label);
        chip.setTag(key);
        chip.setOnClickListener(v -> {
            selectedAddress = key;
            chipLocations.check(chip.getId());
            filterCourts(etSearch != null ? etSearch.getText().toString() : "");
        });
        chipLocations.addView(chip);
        if (selectedAddress.equals(key)) chipLocations.check(chip.getId());
    }

    private boolean hasCourtsForVenue(Integer venueId) {
        if (venueId == null) return false;
        for (JsonObject court : allCourts) {
            if (court.has("venue_id") && !court.get("venue_id").isJsonNull()
                    && court.get("venue_id").getAsInt() == venueId) return true;
        }
        return false;
    }

    private Chip createFilterChip(String label) {
        Chip chip = new Chip(requireContext());
        chip.setId(View.generateViewId());
        chip.setChipBackgroundColorResource(R.color.sport_chip_background);
        chip.setTextColor(requireContext().getColorStateList(R.color.sport_chip_text));
        chip.setChipCornerRadius(getResources().getDisplayMetrics().density * 16);
        chip.setMinHeight((int) (36 * getResources().getDisplayMetrics().density));
        chip.setEnsureMinTouchTargetSize(true);
        chip.setText(label);
        chip.setCheckable(true);
        chip.setClickable(true);
        return chip;
    }

    private void updateSportChips() {
        if (chipSports == null) return;
        chipSports.removeAllViews();
        for (int i = 0; i < sportList.size(); i++) {
            SportItem sport = sportList.get(i);
            if (i > 0 && !hasCourtsForSport(sport.id)) continue;
            Chip chip = createFilterChip(i == 0 ? "All" : (sport.name == null ? "Sport" : sport.name));
            chip.setTag(i);
            final int position = i;
            chip.setOnClickListener(v -> {
                chipSports.check(chip.getId());
                selectedSportId = position == 0 ? null : sport.id;
                filterCourts(etSearch != null ? etSearch.getText().toString() : "");
            });
            chipSports.addView(chip);
            if ((selectedSportId == null && i == 0)
                    || (selectedSportId != null && selectedSportId.equals(sport.id))) chipSports.check(chip.getId());
        }
    }

    private boolean hasCourtsForSport(Integer sportId) {
        if (sportId == null) return true;
        for (JsonObject court : allCourts) {
            if (court.has("sport_id") && !court.get("sport_id").isJsonNull()
                    && court.get("sport_id").getAsInt() == sportId) return true;
        }
        return false;
    }

    private void applyInitialSportFilter() {
        selectedSportId = null;
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
                updateSportChips();
                updateLocationChips();
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
                updateSportChips();
                updateLocationChips();
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

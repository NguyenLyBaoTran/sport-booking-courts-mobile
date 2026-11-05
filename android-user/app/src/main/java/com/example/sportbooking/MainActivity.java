package com.example.sportbooking;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.sportbooking.api.ApiClient;
import com.example.sportbooking.api.AuthApi;
import com.example.sportbooking.api.model.UserResponse;
import com.example.sportbooking.auth.TokenStore;
import com.example.sportbooking.utils.BottomNavUtils;
import com.example.sportbooking.repository.ApiCallback;
import com.example.sportbooking.repository.CourtRepository;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private AuthApi authApi;
    private boolean openingLogin = false;
    private CourtRepository courtRepository;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        authApi = ApiClient.getAuthApi(this);
        courtRepository = new CourtRepository(this);

        String token = TokenStore.getToken(this);

        if (TextUtils.isEmpty(token)) {
            openLogin();
        } else {
            validateToken(token);
        }
    }

    private void validateToken(String token) {
        authApi.getCurrentUser()
                .enqueue(new Callback<UserResponse>() {
                    @Override
                    public void onResponse(
                            Call<UserResponse> call,
                            Response<UserResponse> response
                    ) {
                        if (response.isSuccessful()
                                && response.body() != null
                                && "USER".equals(response.body().getRole())
                                && response.body().isActive()) {
                            showHome(response.body());
                            return;
                        }

                        TokenStore.clearToken(MainActivity.this);
                        openLogin();
                    }

                    @Override
                    public void onFailure(
                            Call<UserResponse> call,
                            Throwable throwable
                    ) {
                        TokenStore.clearToken(MainActivity.this);
                        openLogin();
                    }
                });
    }

    private void showHome(UserResponse user) {
        setContentView(R.layout.activity_main);

        TextView tvWelcome = findViewById(R.id.tvWelcome);
        View btnFindCourt = findViewById(R.id.btnFindCourt);
        View btnMyBookings = findViewById(R.id.btnMyBookings);
        View btnProfile = findViewById(R.id.imgProfileIcon);

        String name = null;

        if (user != null) {
            name = user.getFull_name();

            if (TextUtils.isEmpty(name)) {
                name = user.getEmail();
            }
        }

        tvWelcome.setText(
                TextUtils.isEmpty(name)
                        ? "Welcome to Sport Booking!"
                        : "Welcome, " + name + "!"
        );

        btnFindCourt.setOnClickListener(v ->
                startActivity(new Intent(this, CourtSearchActivity.class))
        );

        btnMyBookings.setOnClickListener(v ->
                startActivity(new Intent(this, BookingsActivity.class))
        );

        loadSports();

        btnProfile.setOnClickListener(v -> {
            startActivity(new Intent(this, ProfileActivity.class));
        });

        BottomNavUtils.setupBottomNav(this, R.id.navHome);
    }

    private void loadSports() {
        RecyclerView recyclerView = findViewById(R.id.rvSports);
        if (recyclerView == null) {
            return;
        }

        recyclerView.setLayoutManager(
                new LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)
        );

        List<JsonObject> sports = new ArrayList<>();
        SportAdapter adapter = new SportAdapter(sports, sport -> {
            Intent intent = new Intent(this, CourtSearchActivity.class);
            intent.putExtra("sport_id", sport.get("id").getAsInt());
            if (sport.has("name") && !sport.get("name").isJsonNull()) {
                intent.putExtra("sport_name", sport.get("name").getAsString());
            }
            startActivity(intent);
        });
        recyclerView.setAdapter(adapter);

        courtRepository.getSports(new ApiCallback<JsonArray>() {
            @Override
            public void onSuccess(JsonArray result) {
                sports.clear();
                for (int i = 0; i < result.size(); i++) {
                    JsonObject sport = result.get(i).getAsJsonObject();
                    if (!sport.has("is_active")
                            || sport.get("is_active").isJsonNull()
                            || sport.get("is_active").getAsBoolean()) {
                        sports.add(sport);
                    }
                }
                adapter.notifyDataSetChanged();
            }

            @Override
            public void onError(String error) {
                sports.clear();
                adapter.notifyDataSetChanged();
            }
        });
    }

    private interface SportClickListener {
        void onSportClick(JsonObject sport);
    }

    private static class SportAdapter extends RecyclerView.Adapter<SportAdapter.ViewHolder> {
        private final List<JsonObject> sports;
        private final SportClickListener listener;

        SportAdapter(List<JsonObject> sports, SportClickListener listener) {
            this.sports = sports;
            this.listener = listener;
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_sport_card, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            JsonObject sport = sports.get(position);
            String name = sport.has("name") && !sport.get("name").isJsonNull()
                    ? sport.get("name").getAsString()
                    : "Sport";
            holder.name.setText(name);
            holder.itemView.setOnClickListener(v -> listener.onSportClick(sport));
        }

        @Override
        public int getItemCount() {
            return sports.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            final TextView name;

            ViewHolder(@NonNull View itemView) {
                super(itemView);
                name = itemView.findViewById(R.id.tvSportName);
            }
        }
    }

    private void openLogin() {
        if (openingLogin || isFinishing()) {
            return;
        }

        openingLogin = true;

        Intent intent = new Intent(
                MainActivity.this,
                LoginActivity.class
        );

        intent.setFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TASK
        );

        startActivity(intent);
        finish();
    }
}

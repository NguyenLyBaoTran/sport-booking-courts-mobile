package com.example.sportbooking.api;

import android.content.Context;

import com.example.sportbooking.BuildConfig;
import com.example.sportbooking.auth.TokenStore;

import okhttp3.OkHttpClient;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public final class ApiClient {

    private static Retrofit retrofit;
    private static AuthApi authApi;
    private static CustomerApi customerApi;

    private ApiClient() {
    }

    private static synchronized Retrofit getRetrofit(Context context) {
        if (retrofit == null) {
            OkHttpClient client = new OkHttpClient.Builder()
                    .connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                    .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                    .writeTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                    .addInterceptor(chain -> {
                        okhttp3.Request.Builder request = chain.request()
                                .newBuilder();

                        String token = TokenStore.getToken(
                                context.getApplicationContext()
                        );

                        if (token != null && !token.trim().isEmpty()) {
                            request.header(
                                    "Authorization",
                                    "Bearer " + token
                            );
                        }

                        return chain.proceed(request.build());
                    })
                    .build();

            retrofit = new Retrofit.Builder()
                    .baseUrl(BuildConfig.API_BASE_URL)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }

        return retrofit;
    }

    public static synchronized AuthApi getAuthApi(Context context) {
        if (authApi == null) {
            authApi = getRetrofit(context).create(AuthApi.class);
        }

        return authApi;
    }

    public static synchronized CustomerApi getCustomerApi(Context context) {
        if (customerApi == null) {
            customerApi = getRetrofit(context).create(CustomerApi.class);
        }

        return customerApi;
    }
}
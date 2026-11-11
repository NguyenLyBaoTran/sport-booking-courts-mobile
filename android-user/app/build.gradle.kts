plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.example.sportbooking"

    compileSdk {
        version = release(37)
    }

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.example.sportbooking"
        minSdk = 24
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        val configuredGatewayUrl = project.findProperty("API_BASE_URL")?.toString()
            ?: "http://10.0.2.2:8000/"
        val gatewayBaseUrl = configuredGatewayUrl.trim().let {
            if (it.endsWith("/")) it else "$it/"
        }

        buildConfigField(
            "String",
            "API_BASE_URL",
            "\"$gatewayBaseUrl\""
        )

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            optimization {
                enable = false
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    implementation(libs.activity.ktx)
    implementation(libs.appcompat)
    implementation(libs.constraintlayout)
    implementation(libs.material)

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    implementation("com.google.zxing:core:3.5.3")

    testImplementation(libs.junit)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.ext.junit)
}
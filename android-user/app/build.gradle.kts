import java.util.Properties

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
            ?: "http://192.168.1.21:8000/"
        val gatewayBaseUrl = configuredGatewayUrl.trim().let {
            if (it.endsWith("/")) it else "$it/"
        }

        buildConfigField(
            "String",
            "API_BASE_URL",
            "\"$gatewayBaseUrl\""
        )

        val googleLocalProperties = Properties().apply {
            val localFile = rootProject.file("google-oauth.local.properties")
            if (localFile.isFile) localFile.inputStream().use { load(it) }
        }
        val gradleGoogleClientId = project.findProperty("GOOGLE_SERVER_CLIENT_ID")?.toString()?.trim().orEmpty()
        val localGoogleClientId = googleLocalProperties.getProperty("GOOGLE_SERVER_CLIENT_ID")?.trim().orEmpty()
        val googleServerClientId = when {
            gradleGoogleClientId.isNotEmpty() && !gradleGoogleClientId.startsWith("your-") -> gradleGoogleClientId
            googleLocalProperties.containsKey("GOOGLE_SERVER_CLIENT_ID") -> localGoogleClientId
            else -> gradleGoogleClientId
        }.ifEmpty { "your-google-oauth-client-id.apps.googleusercontent.com" }
        buildConfigField(
            "String",
            "GOOGLE_SERVER_CLIENT_ID",
            "\"$googleServerClientId\""
        )
        val googleLoginEnabled = project.findProperty("GOOGLE_LOGIN_ENABLED")?.toString()?.toBooleanStrictOrNull()
            ?: googleLocalProperties.getProperty("GOOGLE_LOGIN_ENABLED")?.toBooleanStrictOrNull()
            ?: false
        buildConfigField("boolean", "GOOGLE_LOGIN_ENABLED", googleLoginEnabled.toString())

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
    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.2.1")

    testImplementation(libs.junit)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.ext.junit)
}

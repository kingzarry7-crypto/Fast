plugins {
    id("com.android.application")
}

android {
    namespace = "com.kingzarry.ai"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.kingzarry.ai"
        minSdk = 23
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            // Configure a private upload keystore before producing a Play Store release.
            // Never commit keystore files or passwords to the repository.
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("com.google.androidbrowserhelper:androidbrowserhelper:2.5.0")
}

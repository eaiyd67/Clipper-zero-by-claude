#!/usr/bin/env python3
import os
import shutil
import glob
import sys

ROOT = os.getcwd()
FILES = {}


def write_file(rel_path: str, content: str) -> None:
    full_path = os.path.join(ROOT, rel_path)
    parent = os.path.dirname(full_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.lstrip("\n"))


def copy_ndk_libcpp(android_home: str) -> None:
    abi_to_triple = {
        "arm64-v8a": "aarch64-linux-android",
        "armeabi-v7a": "arm-linux-androideabi",
        "x86_64": "x86_64-linux-android",
        "x86": "i686-linux-android",
    }
    ndk_candidates = sorted(
        glob.glob(os.path.join(android_home, "ndk", "*")),
        reverse=True,
    )
    ndk_bundle = os.path.join(android_home, "ndk-bundle")
    if os.path.isdir(ndk_bundle):
        ndk_candidates.append(ndk_bundle)

    selected_ndk = None
    for cand in ndk_candidates:
        if os.path.isdir(os.path.join(cand, "toolchains", "llvm", "prebuilt")):
            selected_ndk = cand
            break

    if not selected_ndk:
        print("WARNING: No NDK found under ANDROID_HOME; skipping libc++_shared.so copy.")
        return

    prebuilt_dirs = glob.glob(os.path.join(selected_ndk, "toolchains", "llvm", "prebuilt", "*"))
    if not prebuilt_dirs:
        print("WARNING: No LLVM prebuilt directory found in NDK.")
        return
    sysroot_lib = os.path.join(prebuilt_dirs[0], "sysroot", "usr", "lib")

    for abi, triple in abi_to_triple.items():
        src = os.path.join(sysroot_lib, triple, "libc++_shared.so")
        if not os.path.isfile(src):
            print(f"WARNING: Missing {src}")
            continue
        dst_dir = os.path.join(ROOT, "app", "src", "main", "jniLibs", abi)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, "libc++_shared.so"))
        print(f"Copied libc++_shared.so for {abi}")


def write_local_properties() -> str:
    sdk_dir = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or ""
    if sdk_dir:
        escaped = sdk_dir.replace("\\", "\\\\")
        write_file("local.properties", f"sdk.dir={escaped}\n")
        print(f"Wrote local.properties with sdk.dir={sdk_dir}")
    else:
        print("WARNING: ANDROID_HOME not set; local.properties skipped.")
    return sdk_dir


# ---------- GRADLE & PROJECT CONFIG ----------

FILES["settings.gradle.kts"] = r'''
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven { url = uri("https://jitpack.io") }
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}

rootProject.name = "ClipperZero"
include(":app")
'''

FILES["build.gradle.kts"] = r'''
plugins {
    id("com.android.application") version "8.7.2" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
'''

FILES["gradle.properties"] = r'''
org.gradle.jvmargs=-Xmx3072m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
'''

FILES["app/build.gradle.kts"] = r'''
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.clipperzero.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.clipperzero.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64", "x86")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
            pickFirsts += setOf("**/libc++_shared.so")
        }
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    lint {
        abortOnError = false
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.documentfile:documentfile:1.0.1")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")
    implementation("androidx.media3:media3-common:1.4.1")
    implementation("androidx.media3:media3-datasource:1.4.1")

    implementation("io.github.junkfood02.youtubedl-android:library:0.18.1")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1")
    implementation("io.github.junkfood02.youtubedl-android:aria2c:0.18.1")
    implementation("io.github.junkfood02.youtubedl-android:common:0.18.1")
}
'''

FILES["app/proguard-rules.pro"] = r'''
-keep class com.yausername.youtubedl_android.** { *; }
-keep class com.yausername.ffmpeg.** { *; }
-keep class com.yausername.aria2c.** { *; }
'''

# ---------- MANIFEST & RESOURCES ----------

FILES["app/src/main/AndroidManifest.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
    <uses-permission
        android:name="android.permission.READ_EXTERNAL_STORAGE"
        android:maxSdkVersion="32"
        tools:node="replace" />
    <uses-permission
        android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="29"
        tools:node="replace" />

    <application
        android:name=".ClipperZeroApp"
        android:allowBackup="true"
        android:extractNativeLibs="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.ClipperZero"
        android:usesCleartextTraffic="true"
        tools:replace="android:extractNativeLibs">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTask"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="text/plain" />
            </intent-filter>
        </activity>

        <service
            android:name=".service.ExportForegroundService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />

        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
    </application>
</manifest>
'''

FILES["app/src/main/res/xml/file_paths.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<paths>
    <files-path name="internal_files" path="." />
    <cache-path name="cache_files" path="." />
    <external-files-path name="ext_files" path="." />
    <external-path name="external_storage" path="." />
</paths>
'''

FILES["app/src/main/res/values/strings.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Clipper Zero</string>
</resources>
'''

FILES["app/src/main/res/values/themes.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.ClipperZero" parent="android:Theme.Material.NoActionBar">
        <item name="android:statusBarColor">#0B0B0F</item>
        <item name="android:navigationBarColor">#0B0B0F</item>
        <item name="android:windowBackground">#0B0B0F</item>
    </style>
</resources>
'''

FILES["app/src/main/res/drawable/ic_launcher_background.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#0B0B0F"
        android:pathData="M0,0h108v108h-108z" />
    <path
        android:fillColor="#16161D"
        android:pathData="M14,14h80v80h-80z" />
</vector>
'''

FILES["app/src/main/res/drawable/ic_launcher_foreground.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#6366F1"
        android:pathData="M34,32 L76,54 L34,76 Z" />
    <path
        android:fillColor="#EF4444"
        android:pathData="M26,44 L32,44 L32,64 L26,64 Z" />
    <path
        android:fillColor="#06B6D4"
        android:pathData="M78,36 L84,36 L84,72 L78,72 Z" />
</vector>
'''

FILES["app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
'''

FILES["app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml"] = r'''
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
'''

# ---------- DOMAIN MODELS ----------

FILES["app/src/main/java/com/clipperzero/app/domain/model/AppResult.kt"] = r'''
package com.clipperzero.app.domain.model

sealed class AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>()
    data class Error(val message: String, val cause: Throwable? = null) : AppResult<Nothing>()
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/Signal.kt"] = r'''
package com.clipperzero.app.domain.model

enum class SignalType(val label: String) {
    HEATMAP("Heatmap"),
    SUPER_CHAT("Super Chat"),
    CHAT_HYPE("Chat Hype"),
    AI_PICK("AI Pick"),
    TRANSCRIPT("Transcript"),
    CUSTOM("Custom")
}

data class SuperChatInfo(
    val author: String,
    val amountDisplay: String,
    val message: String,
    val timestampSec: Double
)

data class Signal(
    val startSec: Double,
    val endSec: Double,
    val score: Double,
    val type: SignalType,
    val label: String = "",
    val superChat: SuperChatInfo? = null
)
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/ClipCandidate.kt"] = r'''
package com.clipperzero.app.domain.model

import java.util.UUID

data class ViralCopy(
    val title: String,
    val hook: String,
    val hashtags: List<String>
) {
    fun formattedPack(): String {
        val tags = hashtags.joinToString(" ")
        return "$title\n\n$hook\n\n$tags".trim()
    }
}

data class ClipCandidate(
    val id: String = UUID.randomUUID().toString(),
    val startSec: Double,
    val endSec: Double,
    val score: Double,
    val primaryType: SignalType,
    val signalTypes: Set<SignalType> = setOf(primaryType),
    val reason: String,
    val superChat: SuperChatInfo? = null,
    val viralCopy: ViralCopy? = null
) {
    val isMultiSignal: Boolean
        get() = signalTypes.size >= 2

    val durationSec: Double
        get() = (endSec - startSec).coerceAtLeast(1.0)
}

enum class PaddingPreset(val label: String, val preSec: Double, val postSec: Double) {
    TIGHT("Tight (-2s/+3s)", 2.0, 3.0),
    BALANCED("Balanced (-5s/+6s)", 5.0, 6.0),
    CONTEXT("Context (-10s/+10s)", 10.0, 10.0)
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/VideoMetadata.kt"] = r'''
package com.clipperzero.app.domain.model

data class HeatmapPoint(
    val startTime: Double,
    val endTime: Double,
    val value: Double
)

data class TranscriptSegment(
    val startSec: Double,
    val endSec: Double,
    val text: String
)

enum class SourceKind {
    YOUTUBE,
    FACEBOOK,
    LOCAL,
    OTHER
}

data class VideoMetadata(
    val id: String,
    val sourceUrl: String,
    val normalizedUrl: String,
    val title: String,
    val uploader: String,
    val durationSec: Double,
    val isLiveVod: Boolean,
    val sourceKind: SourceKind,
    val previewStreamUrl: String?,
    val heatmap: List<HeatmapPoint>,
    val transcript: List<TranscriptSegment>,
    val liveChatFilePath: String?,
    val localUri: String? = null
)
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/AiConfig.kt"] = r'''
package com.clipperzero.app.domain.model

enum class AiProviderPreset(
    val displayName: String,
    val defaultBaseUrl: String,
    val defaultModels: List<String>
) {
    DEEPSEEK(
        displayName = "DeepSeek",
        defaultBaseUrl = "https://api.deepseek.com/v1",
        defaultModels = listOf("deepseek-chat", "deepseek-reasoner")
    ),
    GEMINI(
        displayName = "Gemini",
        defaultBaseUrl = "https://generativelanguage.googleapis.com/v1beta/openai",
        defaultModels = listOf("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro")
    ),
    OPENROUTER(
        displayName = "OpenRouter",
        defaultBaseUrl = "https://openrouter.ai/api/v1",
        defaultModels = listOf(
            "deepseek/deepseek-chat",
            "google/gemini-2.0-flash-001",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-haiku",
            "meta-llama/llama-3.3-70b-instruct"
        )
    ),
    CUSTOM(
        displayName = "Custom",
        defaultBaseUrl = "https://api.openai.com/v1",
        defaultModels = listOf("gpt-4o-mini", "gpt-4o")
    )
}

data class AiConfig(
    val preset: AiProviderPreset = AiProviderPreset.DEEPSEEK,
    val baseUrl: String = AiProviderPreset.DEEPSEEK.defaultBaseUrl,
    val primaryKey: String = "",
    val backupKey: String = "",
    val model: String = AiProviderPreset.DEEPSEEK.defaultModels.first(),
    val offlineMode: Boolean = false,
    val isConnected: Boolean = false,
    val lastStatusMessage: String = "Not connected"
)
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/ExportModels.kt"] = r'''
package com.clipperzero.app.domain.model

import java.util.UUID

data class ExportOptions(
    val fastCut: Boolean = true,
    val cropVertical916: Boolean = false,
    val cropOffsetX: Float = 0.5f,
    val superChatOverlay: Boolean = false,
    val audioLoudnorm: Boolean = false,
    val writeSidecarTxt: Boolean = true
)

enum class ExportStatus {
    QUEUED,
    RUNNING,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class ExportJob(
    val id: String = UUID.randomUUID().toString(),
    val clipId: String,
    val title: String,
    val sourceUrl: String,
    val localUri: String?,
    val startSec: Double,
    val endSec: Double,
    val options: ExportOptions,
    val superChat: SuperChatInfo?,
    val viralCopy: ViralCopy?,
    val status: ExportStatus = ExportStatus.QUEUED,
    val progress: Float = 0f,
    val stage: String = "Queued",
    val outputUri: String? = null,
    val outputPath: String? = null,
    val errorMessage: String? = null,
    val createdAtMs: Long = System.currentTimeMillis()
)

enum class StoragePreset(val label: String, val relativeSubdir: String) {
    MOVIES("Movies/ClipPulse", "Movies/ClipPulse"),
    DOWNLOADS("Download/ClipPulse", "Download/ClipPulse"),
    DCIM("DCIM/ClipPulse", "DCIM/ClipPulse"),
    CUSTOM_SAF("Custom Folder (SAF)", "Custom")
}

data class StorageConfig(
    val preset: StoragePreset = StoragePreset.MOVIES,
    val safTreeUri: String? = null,
    val safDisplayName: String? = null
)
'''

FILES["app/src/main/java/com/clipperzero/app/domain/model/ScanHistoryItem.kt"] = r'''
package com.clipperzero.app.domain.model

data class ScanHistoryItem(
    val url: String,
    val title: String,
    val uploader: String,
    val durationSec: Double,
    val clipCount: Int,
    val scannedAtMs: Long
)
'''

# ---------- UTILITIES ----------

FILES["app/src/main/java/com/clipperzero/app/util/UrlNormalizer.kt"] = r'''
package com.clipperzero.app.util

import android.net.Uri
import com.clipperzero.app.domain.model.SourceKind

object UrlNormalizer {

    private val urlRegex = Regex("""https?://[^\s<>"']+""", RegexOption.IGNORE_CASE)
    private val ytIdRegex = Regex("""^[A-Za-z0-9_-]{11}$""")

    fun extractFirstUrl(rawInput: String): String {
        val trimmed = rawInput.trim()
        if (trimmed.startsWith("content://") || trimmed.startsWith("file://")) {
            return trimmed
        }
        val match = urlRegex.find(trimmed)
        return match?.value?.trimEnd('.', ',', ')', ']', '"', '\'') ?: trimmed
    }

    fun normalize(rawInput: String): Pair<String, SourceKind> {
        val extracted = extractFirstUrl(rawInput)
        if (extracted.startsWith("content://") || extracted.startsWith("file://")) {
            return extracted to SourceKind.LOCAL
        }

        val uri = try {
            Uri.parse(extracted)
        } catch (_: Exception) {
            return extracted to SourceKind.OTHER
        }

        val host = (uri.host ?: "").lowercase()
        val isYouTube = host.contains("youtube.com") || host.contains("youtu.be")
        val isFacebook = host.contains("facebook.com") || host.contains("fb.watch") || host.contains("fb.com")

        if (isYouTube) {
            val videoId = extractYouTubeId(uri)
            if (videoId != null) {
                return "https://www.youtube.com/watch?v=$videoId" to SourceKind.YOUTUBE
            }
            return extracted to SourceKind.YOUTUBE
        }

        if (isFacebook) {
            return extracted to SourceKind.FACEBOOK
        }

        return extracted to SourceKind.OTHER
    }

    private fun extractYouTubeId(uri: Uri): String? {
        val host = (uri.host ?: "").lowercase()
        val segments = uri.pathSegments ?: emptyList()

        if (host.contains("youtu.be")) {
            val first = segments.firstOrNull()
            if (first != null && ytIdRegex.matches(first)) return first
        }

        val vParam = uri.getQueryParameter("v")
        if (vParam != null && ytIdRegex.matches(vParam)) return vParam

        if (segments.size >= 2) {
            val prefix = segments[0].lowercase()
            if (prefix == "live" || prefix == "shorts" || prefix == "embed" || prefix == "v") {
                val candidate = segments[1]
                if (ytIdRegex.matches(candidate)) return candidate
            }
        }
        return null
    }

    fun normalizeAiBaseUrl(rawUrl: String): String {
        var cleaned = rawUrl.trim().trimEnd('/')
        if (cleaned.isEmpty()) return ""
        if (!cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
            cleaned = "https://$cleaned"
        }
        if (cleaned.endsWith("/chat/completions")) {
            cleaned = cleaned.removeSuffix("/chat/completions")
        }
        return cleaned.trimEnd('/')
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/util/ErrorSanitizer.kt"] = r'''
package com.clipperzero.app.util

object ErrorSanitizer {
    private val longUrlRegex = Regex("""https?://[^\s]{40,}""")
    private val multiSpaceRegex = Regex("""\s+""")

    fun sanitize(raw: String?, fallback: String = "Operation failed"): String {
        if (raw.isNullOrBlank()) return fallback
        val stripped = longUrlRegex.replace(raw, "[url]")
            .replace("\r", " ")
            .replace("\n", " ")
            .let { multiSpaceRegex.replace(it, " ").trim() }
        return if (stripped.length > 220) {
            stripped.take(217) + "..."
        } else {
            stripped.ifBlank { fallback }
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/util/TimeFormatters.kt"] = r'''
package com.clipperzero.app.util

import java.util.Locale
import kotlin.math.floor

object TimeFormatters {

    fun formatTimestamp(seconds: Double): String {
        val clamped = seconds.coerceAtLeast(0.0)
        val totalSec = floor(clamped).toLong()
        val hours = totalSec / 3600L
        val minutes = (totalSec % 3600L) / 60L
        val secs = totalSec % 60L
        return if (hours > 0L) {
            String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, secs)
        } else {
            String.format(Locale.US, "%02d:%02d", minutes, secs)
        }
    }

    fun formatFfmpegTime(seconds: Double): String {
        val clamped = seconds.coerceAtLeast(0.0)
        val totalMillis = (clamped * 1000.0).toLong()
        val hours = totalMillis / 3600000L
        val minutes = (totalMillis % 3600000L) / 60000L
        val secs = (totalMillis % 60000L) / 1000L
        val millis = totalMillis % 1000L
        return String.format(Locale.US, "%02d:%02d:%02d.%03d", hours, minutes, secs, millis)
    }

    fun formatSectionRange(startSec: Double, endSec: Double): String {
        val s = startSec.coerceAtLeast(0.0)
        val e = endSec.coerceAtLeast(s + 1.0)
        return String.format(Locale.US, "*%.2f-%.2f", s, e)
    }

    fun parseTimeToSeconds(input: String): Double? {
        val clean = input.trim()
        if (clean.isEmpty()) return null
        val parts = clean.split(":")
        return try {
            when (parts.size) {
                1 -> parts[0].toDouble()
                2 -> parts[0].toLong() * 60.0 + parts[1].toDouble()
                3 -> parts[0].toLong() * 3600.0 + parts[1].toLong() * 60.0 + parts[2].toDouble()
                else -> null
            }
        } catch (_: Exception) {
            null
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/util/JsonUtils.kt"] = r'''
package com.clipperzero.app.util

import org.json.JSONArray
import org.json.JSONObject

object JsonUtils {

    fun extractStrictJsonObject(raw: String): JSONObject? {
        val trimmed = raw.trim()
        try {
            return JSONObject(trimmed)
        } catch (_: Exception) {
        }

        val cleaned = trimmed
            .removePrefix("```json")
            .removePrefix("```JSON")
            .removePrefix("```")
            .removeSuffix("```")
            .trim()
        try {
            return JSONObject(cleaned)
        } catch (_: Exception) {
        }

        val start = cleaned.indexOf('{')
        val end = cleaned.lastIndexOf('}')
        if (start >= 0 && end > start) {
            val slice = cleaned.substring(start, end + 1)
            try {
                return JSONObject(slice)
            } catch (_: Exception) {
            }
        }
        return null
    }

    fun extractStrictJsonArray(raw: String): JSONArray? {
        val trimmed = raw.trim()
        try {
            return JSONArray(trimmed)
        } catch (_: Exception) {
        }

        val start = trimmed.indexOf('[')
        val end = trimmed.lastIndexOf(']')
        if (start >= 0 && end > start) {
            val slice = trimmed.substring(start, end + 1)
            try {
                return JSONArray(slice)
            } catch (_: Exception) {
            }
        }
        return null
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/util/FfmpegRunner.kt"] = r'''
package com.clipperzero.app.util

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.util.concurrent.atomic.AtomicReference

data class FfmpegResult(
    val exitCode: Int,
    val outputTail: String
) {
    val isSuccess: Boolean get() = exitCode == 0
}

class FfmpegRunner(private val context: Context) {

    private val activeProcess = AtomicReference<Process?>(null)

    fun cancelCurrent() {
        activeProcess.getAndSet(null)?.destroyForcibly()
    }

    fun findFfmpegBinary(): File? {
        val roots = listOfNotNull(
            File(context.noBackupFilesDir, "youtubedl-android"),
            File(context.filesDir, "youtubedl-android")
        )
        for (root in roots) {
            val direct = File(root, "packages/ffmpeg/usr/bin/ffmpeg")
            if (direct.exists()) {
                direct.setExecutable(true)
                return direct
            }
            if (root.exists()) {
                val found = root.walkTopDown()
                    .maxDepth(6)
                    .firstOrNull { it.isFile && it.name == "ffmpeg" }
                if (found != null) {
                    found.setExecutable(true)
                    return found
                }
            }
        }
        val nativeBin = File(context.applicationInfo.nativeLibraryDir, "libffmpeg.so")
        if (nativeBin.exists()) return nativeBin
        return null
    }

    fun buildLdLibraryPath(): String {
        val libDirs = LinkedHashSet<String>()
        val roots = listOfNotNull(
            File(context.noBackupFilesDir, "youtubedl-android/packages"),
            File(context.filesDir, "youtubedl-android/packages")
        )
        for (packagesDir in roots) {
            if (!packagesDir.exists()) continue
            packagesDir.listFiles()?.forEach { pkg ->
                if (pkg.isDirectory) {
                    val usrLib = File(pkg, "usr/lib")
                    if (usrLib.isDirectory) libDirs.add(usrLib.absolutePath)
                    val lib = File(pkg, "lib")
                    if (lib.isDirectory) libDirs.add(lib.absolutePath)
                }
            }
        }
        val nativeDir = context.applicationInfo.nativeLibraryDir
        if (!nativeDir.isNullOrBlank()) {
            libDirs.add(nativeDir)
        }
        return libDirs.joinToString(File.pathSeparator)
    }

    suspend fun run(
        args: List<String>,
        onLogLine: ((String) -> Unit)? = null
    ): FfmpegResult = withContext(Dispatchers.IO) {
        val binary = findFfmpegBinary()
            ?: return@withContext FfmpegResult(-1, "FFmpeg binary not found in youtubedl-android packages")

        val cmd = ArrayList<String>(args.size + 1)
        cmd.add(binary.absolutePath)
        cmd.addAll(args)

        val pb = ProcessBuilder(cmd)
        pb.redirectErrorStream(true)
        val env = pb.environment()
        val existingLd = env["LD_LIBRARY_PATH"].orEmpty()
        val computedLd = buildLdLibraryPath()
        env["LD_LIBRARY_PATH"] = if (existingLd.isNotBlank()) {
            "$computedLd${File.pathSeparator}$existingLd"
        } else {
            computedLd
        }

        val tailLines = ArrayDeque<String>(25)
        try {
            val process = pb.start()
            activeProcess.set(process)
            BufferedReader(InputStreamReader(process.inputStream)).use { reader ->
                var line = reader.readLine()
                while (line != null) {
                    if (tailLines.size >= 25) tailLines.removeFirst()
                    tailLines.addLast(line)
                    onLogLine?.invoke(line)
                    line = reader.readLine()
                }
            }
            val exitCode = process.waitFor()
            activeProcess.compareAndSet(process, null)
            FfmpegResult(exitCode, tailLines.joinToString("\n"))
        } catch (e: Exception) {
            activeProcess.set(null)
            FfmpegResult(-1, ErrorSanitizer.sanitize(e.message, "FFmpeg execution failed"))
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/util/SuperChatOverlayRenderer.kt"] = r'''
package com.clipperzero.app.util

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import com.clipperzero.app.domain.model.SuperChatInfo
import java.io.File
import java.io.FileOutputStream

object SuperChatOverlayRenderer {

    fun renderToPng(info: SuperChatInfo, outFile: File): File {
        val width = 720
        val padding = 28
        val headerHeight = 84

        val msgPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textSize = 30f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }

        val messageText = info.message.ifBlank { "Super Chat!" }.take(180)
        val staticLayout = StaticLayout.Builder
            .obtain(messageText, 0, messageText.length, msgPaint, width - padding * 2)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setLineSpacing(6f, 1.0f)
            .setMaxLines(4)
            .build()

        val bodyHeight = (staticLayout.height + padding * 2).coerceAtLeast(88)
        val totalHeight = headerHeight + bodyHeight

        val bitmap = Bitmap.createBitmap(width, totalHeight, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.TRANSPARENT)

        val bodyBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#E616161D")
        }
        val headerBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#FFF59E0B")
        }
        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#FFF59E0B")
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }

        val fullRect = RectF(2f, 2f, width - 2f, totalHeight - 2f)
        canvas.drawRoundRect(fullRect, 24f, 24f, bodyBgPaint)

        val headerRect = RectF(2f, 2f, width - 2f, headerHeight.toFloat())
        canvas.drawRoundRect(headerRect, 24f, 24f, headerBgPaint)
        canvas.drawRect(2f, headerHeight - 24f, width - 2f, headerHeight.toFloat(), headerBgPaint)

        val authorPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#0B0B0F")
            textSize = 28f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val amountPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#0B0B0F")
            textSize = 30f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            textAlign = Paint.Align.RIGHT
        }

        canvas.drawText(info.author.take(28), padding.toFloat(), 52f, authorPaint)
        canvas.drawText(info.amountDisplay.take(18), (width - padding).toFloat(), 52f, amountPaint)

        canvas.save()
        canvas.translate(padding.toFloat(), (headerHeight + padding).toFloat())
        staticLayout.draw(canvas)
        canvas.restore()

        canvas.drawRoundRect(fullRect, 24f, 24f, borderPaint)

        outFile.parentFile?.mkdirs()
        FileOutputStream(outFile).use { fos ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos)
        }
        bitmap.recycle()
        return outFile
    }
}
'''

# ---------- DETECTION ENGINES ----------

FILES["app/src/main/java/com/clipperzero/app/domain/engine/HeatmapEngine.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.HeatmapPoint
import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType

class HeatmapEngine {

    fun detect(points: List<HeatmapPoint>, durationSec: Double): List<Signal> {
        if (points.size < 3 || durationSec <= 0.0) return emptyList()

        val values = points.map { it.value }
        val mean = values.average()
        val maxVal = values.maxOrNull() ?: 0.0
        if (maxVal <= 0.0) return emptyList()

        val threshold = (mean * 1.25).coerceAtMost(maxVal * 0.72).coerceAtLeast(0.35)
        val peaks = mutableListOf<Int>()

        for (i in 1 until points.size - 1) {
            val v = points[i].value
            if (v >= threshold && v >= points[i - 1].value && v >= points[i + 1].value) {
                peaks.add(i)
            }
        }

        if (peaks.isEmpty()) {
            val maxIdx = points.indices.maxByOrNull { points[it].value } ?: return emptyList()
            peaks.add(maxIdx)
        }

        val signals = mutableListOf<Signal>()
        for (peakIdx in peaks) {
            var left = peakIdx
            while (left > 0 && points[left - 1].value <= points[left].value) {
                left--
            }
            var right = peakIdx
            while (right < points.size - 1 && points[right + 1].value <= points[right].value) {
                right++
            }

            var start = points[left].startTime.coerceAtLeast(0.0)
            var end = points[right].endTime.coerceAtMost(durationSec)

            val span = end - start
            val center = (points[peakIdx].startTime + points[peakIdx].endTime) / 2.0
            if (span < 12.0) {
                start = (center - 8.0).coerceAtLeast(0.0)
                end = (center + 10.0).coerceAtMost(durationSec)
            } else if (span > 65.0) {
                start = (center - 25.0).coerceAtLeast(0.0)
                end = (center + 25.0).coerceAtMost(durationSec)
            }

            val normScore = (points[peakIdx].value / maxVal).coerceIn(0.1, 1.0)
            signals.add(
                Signal(
                    startSec = start,
                    endSec = end,
                    score = normScore,
                    type = SignalType.HEATMAP,
                    label = "Most replayed peak (${(normScore * 100.0).toInt()}%)"
                )
            )
        }

        return signals.sortedByDescending { it.score }.take(15)
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/engine/SuperChatEngine.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.domain.model.SuperChatInfo
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.InputStreamReader

class SuperChatEngine {

    fun detectFromLiveChatFile(filePath: String?, durationSec: Double): List<Signal> {
        if (filePath.isNullOrBlank()) return emptyList()
        val file = File(filePath)
        if (!file.exists() || !file.isFile) return emptyList()

        val signals = mutableListOf<Signal>()
        try {
            BufferedReader(InputStreamReader(FileInputStream(file), Charsets.UTF_8), 16384).use { reader ->
                var line = reader.readLine()
                while (line != null) {
                    if (line.contains("liveChatPaidMessageRenderer") || line.contains("liveChatPaidStickerRenderer")) {
                        parsePaidLine(line, durationSec)?.let { signals.add(it) }
                    }
                    line = reader.readLine()
                }
            }
        } catch (_: Exception) {
        }
        return signals.sortedByDescending { it.score }.take(20)
    }

    private fun parsePaidLine(line: String, durationSec: Double): Signal? {
        return try {
            val root = JSONObject(line)
            val offsetMsec = root.optLong("videoOffsetTimeMsec", -1L)
                .let { if (it >= 0L) it else extractNestedOffset(root) }
            if (offsetMsec < 0L) return null

            val sec = offsetMsec / 1000.0
            if (durationSec > 0.0 && sec > durationSec) return null

            val renderer = findPaidRenderer(root) ?: return null
            val author = renderer.optJSONObject("authorName")?.optString("simpleText")
                ?.takeIf { it.isNotBlank() } ?: "Viewer"
            val amount = renderer.optJSONObject("purchaseAmountText")?.optString("simpleText")
                ?.takeIf { it.isNotBlank() } ?: "Super Chat"
            val message = extractRunsText(renderer.optJSONObject("message"))

            val numericValue = Regex("""[\d,.]+""").find(amount)?.value
                ?.replace(",", "")?.toDoubleOrNull() ?: 5.0
            val score = (0.65 + (numericValue / 100.0).coerceAtMost(0.35)).coerceIn(0.65, 1.0)

            val start = (sec - 4.0).coerceAtLeast(0.0)
            val end = if (durationSec > 0.0) (sec + 22.0).coerceAtMost(durationSec) else sec + 22.0

            val sc = SuperChatInfo(
                author = author,
                amountDisplay = amount,
                message = message,
                timestampSec = sec
            )
            Signal(
                startSec = start,
                endSec = end,
                score = score,
                type = SignalType.SUPER_CHAT,
                label = "$amount from $author",
                superChat = sc
            )
        } catch (_: Exception) {
            null
        }
    }

    private fun extractNestedOffset(root: JSONObject): Long {
        val replay = root.optJSONObject("replayChatItemAction")
        return replay?.optString("videoOffsetTimeMsec")?.toLongOrNull() ?: -1L
    }

    private fun findPaidRenderer(root: JSONObject): JSONObject? {
        val replay = root.optJSONObject("replayChatItemAction") ?: return null
        val actions = replay.optJSONArray("actions") ?: return null
        for (i in 0 until actions.length()) {
            val action = actions.optJSONObject(i) ?: continue
            val item = action.optJSONObject("addChatItemAction")?.optJSONObject("item") ?: continue
            item.optJSONObject("liveChatPaidMessageRenderer")?.let { return it }
            item.optJSONObject("liveChatPaidStickerRenderer")?.let { return it }
        }
        return null
    }

    private fun extractRunsText(obj: JSONObject?): String {
        if (obj == null) return ""
        val simple = obj.optString("simpleText", "")
        if (simple.isNotBlank()) return simple
        val runs = obj.optJSONArray("runs") ?: return ""
        val sb = StringBuilder()
        for (i in 0 until runs.length()) {
            val run = runs.optJSONObject(i) ?: continue
            val text = run.optString("text", "")
            if (text.isNotEmpty()) sb.append(text)
        }
        return sb.toString().trim()
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/engine/ChatVelocityEngine.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.InputStreamReader
import kotlin.math.sqrt

class ChatVelocityEngine {

    fun detectFromLiveChatFile(filePath: String?, durationSec: Double): List<Signal> {
        if (filePath.isNullOrBlank()) return emptyList()
        val file = File(filePath)
        if (!file.exists() || !file.isFile) return emptyList()

        val bucketSizeSec = 10
        val counts = HashMap<Int, Int>()

        try {
            BufferedReader(InputStreamReader(FileInputStream(file), Charsets.UTF_8), 16384).use { reader ->
                var line = reader.readLine()
                while (line != null) {
                    val msec = extractOffsetFast(line)
                    if (msec >= 0L) {
                        val sec = (msec / 1000L).toInt()
                        if (durationSec <= 0.0 || sec <= durationSec) {
                            val bucket = sec / bucketSizeSec
                            counts[bucket] = (counts[bucket] ?: 0) + 1
                        }
                    }
                    line = reader.readLine()
                }
            }
        } catch (_: Exception) {
            return emptyList()
        }

        if (counts.size < 4) return emptyList()

        val values = counts.values.map { it.toDouble() }
        val mean = values.average()
        val variance = values.map { (it - mean) * (it - mean) }.average()
        val stdDev = sqrt(variance).coerceAtLeast(1.0)
        val threshold = mean + stdDev * 1.6
        val maxCount = values.maxOrNull()?.coerceAtLeast(1.0) ?: 1.0

        val signals = mutableListOf<Signal>()
        for ((bucket, count) in counts) {
            if (count.toDouble() >= threshold && count >= 5) {
                val start = (bucket * bucketSizeSec - 5).toDouble().coerceAtLeast(0.0)
                val endRaw = ((bucket + 1) * bucketSizeSec + 12).toDouble()
                val end = if (durationSec > 0.0) endRaw.coerceAtMost(durationSec) else endRaw
                val score = (count.toDouble() / maxCount).coerceIn(0.4, 1.0)
                signals.add(
                    Signal(
                        startSec = start,
                        endSec = end,
                        score = score,
                        type = SignalType.CHAT_HYPE,
                        label = "Chat spike ($count msgs/10s)"
                    )
                )
            }
        }

        return signals.sortedByDescending { it.score }.take(15)
    }

    private fun extractOffsetFast(line: String): Long {
        val key = "\"videoOffsetTimeMsec\""
        val idx = line.indexOf(key)
        if (idx >= 0) {
            val colon = line.indexOf(':', idx + key.length)
            if (colon > 0) {
                var i = colon + 1
                while (i < line.length && (line[i] == ' ' || line[i] == '"')) i++
                val start = i
                while (i < line.length && line[i].isDigit()) i++
                if (i > start) {
                    return line.substring(start, i).toLongOrNull() ?: -1L
                }
            }
        }
        return try {
            val obj = JSONObject(line)
            obj.optLong("videoOffsetTimeMsec", -1L)
        } catch (_: Exception) {
            -1L
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/engine/TranscriptExcitementEngine.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.domain.model.TranscriptSegment

class TranscriptExcitementEngine {

    private val excitementTokens = listOf(
        "no way", "oh my god", "omg", "insane", "crazy", "clutch", "unbelievable",
        "wait what", "let's go", "lets go", "wtf", "bro what", "holy", "destroyed",
        "exposed", "plot twist", "secret", "shocking", "genius", "impossible",
        "bhai", "kya baat", "arey", "pagal", "khatarnak", "gajab", "bawal",
        "sach mein", "maza aa gaya", "dhamaka", "ओह माय गॉड", "गजब", "कमाल", "बवाल",
        "darun", "osthir", "ki holo", "bhai re", "amar matha", "shera", "pagol",
        "অস্থির", "দারুণ", "সেরা", "কি হলো", "বিশ্বাস", "অসম্ভব", "ভাই"
    )

    fun detect(segments: List<TranscriptSegment>, durationSec: Double): List<Signal> {
        if (segments.isEmpty()) return emptyList()

        val scored = mutableListOf<Signal>()
        for (i in segments.indices) {
            val seg = segments[i]
            val lower = seg.text.lowercase()
            var hits = 0
            for (token in excitementTokens) {
                if (lower.contains(token)) hits++
            }
            val exclamations = seg.text.count { it == '!' || it == '?' }
            val allCapsWords = seg.text.split(" ").count { w ->
                w.length >= 4 && w.all { ch -> ch.isUpperCase() }
            }

            val rawScore = hits * 0.35 + exclamations * 0.12 + allCapsWords * 0.15
            if (rawScore >= 0.35) {
                val start = (seg.startSec - 4.0).coerceAtLeast(0.0)
                val endRaw = (seg.endSec + 14.0).coerceAtLeast(start + 15.0)
                val end = if (durationSec > 0.0) endRaw.coerceAtMost(durationSec) else endRaw
                scored.add(
                    Signal(
                        startSec = start,
                        endSec = end,
                        score = rawScore.coerceIn(0.35, 0.95),
                        type = SignalType.TRANSCRIPT,
                        label = seg.text.take(64)
                    )
                )
            }
        }
        return scored.sortedByDescending { it.score }.take(15)
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/engine/ConsensusMerger.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.PaddingPreset
import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import kotlin.math.max
import kotlin.math.min

class ConsensusMerger {

    fun merge(
        signals: List<Signal>,
        durationSec: Double,
        padding: PaddingPreset = PaddingPreset.BALANCED,
        mergeWindowSec: Double = 18.0
    ): List<ClipCandidate> {
        if (signals.isEmpty()) {
            return buildFallbackClips(durationSec)
        }

        val sorted = signals.sortedBy { it.startSec }
        val clusters = mutableListOf<MutableList<Signal>>()

        for (sig in sorted) {
            val lastCluster = clusters.lastOrNull()
            if (lastCluster == null) {
                clusters.add(mutableListOf(sig))
            } else {
                val clusterEnd = lastCluster.maxOf { it.endSec }
                if (sig.startSec <= clusterEnd + mergeWindowSec) {
                    lastCluster.add(sig)
                } else {
                    clusters.add(mutableListOf(sig))
                }
            }
        }

        val candidates = clusters.map { cluster ->
            val rawStart = cluster.minOf { it.startSec }
            val rawEnd = cluster.maxOf { it.endSec }

            var start = (rawStart - padding.preSec).coerceAtLeast(0.0)
            var end = rawEnd + padding.postSec
            if (durationSec > 0.0) {
                end = end.coerceAtMost(durationSec)
            }
            if (end - start > 90.0) {
                val top = cluster.maxByOrNull { it.score } ?: cluster.first()
                val center = (top.startSec + top.endSec) / 2.0
                start = (center - 30.0).coerceAtLeast(0.0)
                end = if (durationSec > 0.0) (center + 30.0).coerceAtMost(durationSec) else center + 30.0
            }
            if (end - start < 5.0) {
                end = if (durationSec > 0.0) (start + 15.0).coerceAtMost(durationSec) else start + 15.0
            }

            val types = cluster.map { it.type }.toSet()
            val primary = cluster.maxByOrNull { it.score }?.type ?: SignalType.HEATMAP
            val baseScore = cluster.maxOf { it.score }
            val multiBoost = if (types.size >= 2) 0.15 * (types.size - 1) else 0.0
            val finalScore = (baseScore + multiBoost).coerceIn(0.1, 1.0)
            val superChat = cluster.firstNotNullOfOrNull { it.superChat }
            val reasons = cluster.mapNotNull { it.label.takeIf { l -> l.isNotBlank() } }
                .distinct()
                .take(2)
                .joinToString(" + ")
                .ifBlank { primary.label }

            ClipCandidate(
                startSec = start,
                endSec = end,
                score = finalScore,
                primaryType = primary,
                signalTypes = types,
                reason = reasons,
                superChat = superChat
            )
        }

        return candidates.sortedByDescending { it.score }
    }

    private fun buildFallbackClips(durationSec: Double): List<ClipCandidate> {
        if (durationSec <= 0.0) return emptyList()
        val clipLen = min(45.0, max(15.0, durationSec / 4.0))
        val count = if (durationSec < 60.0) 1 else min(4, (durationSec / clipLen).toInt().coerceAtLeast(1))
        val step = (durationSec - clipLen).coerceAtLeast(0.0) / max(1, count - 1)
        val result = mutableListOf<ClipCandidate>()
        for (i in 0 until count) {
            val start = (i * step).coerceAtLeast(0.0)
            val end = (start + clipLen).coerceAtMost(durationSec)
            result.add(
                ClipCandidate(
                    startSec = start,
                    endSec = end,
                    score = 0.5 - i * 0.05,
                    primaryType = SignalType.HEATMAP,
                    signalTypes = setOf(SignalType.HEATMAP),
                    reason = "Highlight segment ${i + 1}"
                )
            )
        }
        return result
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/domain/engine/ViralCopyGenerator.kt"] = r'''
package com.clipperzero.app.domain.engine

import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.domain.model.VideoMetadata
import com.clipperzero.app.domain.model.ViralCopy
import com.clipperzero.app.util.TimeFormatters

object ViralCopyGenerator {

    fun generateOffline(video: VideoMetadata, clip: ClipCandidate): ViralCopy {
        val cleanTitle = video.title.take(48).trim().ifBlank { "Epic Moment" }
        val stamp = TimeFormatters.formatTimestamp(clip.startSec)

        val title = when {
            clip.superChat != null -> "${clip.superChat.amountDisplay} Super Chat Reaction - $cleanTitle"
            clip.isMultiSignal -> "Peak Viral Moment ($stamp) | $cleanTitle"
            clip.primaryType == SignalType.HEATMAP -> "Most Replayed Clip ($stamp) | $cleanTitle"
            clip.primaryType == SignalType.CHAT_HYPE -> "Chat Went Wild at $stamp | $cleanTitle"
            clip.primaryType == SignalType.AI_PICK -> "Must-Watch Highlight | $cleanTitle"
            else -> "Highlight at $stamp | $cleanTitle"
        }

        val hook = when {
            clip.superChat != null -> "${clip.superChat.author} dropped ${clip.superChat.amountDisplay}: \"${clip.superChat.message.take(80)}\""
            clip.reason.isNotBlank() -> "Watch what happens here: ${clip.reason}"
            else -> "Wait until the end of this clip from ${video.uploader.ifBlank { "the stream" }}."
        }

        val baseTags = mutableListOf("#shorts", "#clips", "#viral", "#highlights")
        if (video.isLiveVod) baseTags.add("#livestream")
        if (clip.superChat != null) baseTags.add("#superchat")
        val uploaderTag = video.uploader
            .replace(Regex("[^A-Za-z0-9]"), "")
            .lowercase()
            .take(18)
        if (uploaderTag.length >= 3) {
            baseTags.add("#$uploaderTag")
        }

        return ViralCopy(
            title = title,
            hook = hook,
            hashtags = baseTags.distinct().take(6)
        )
    }
}
'''

# ---------- DATA LAYER ----------

FILES["app/src/main/java/com/clipperzero/app/data/PreferencesStore.kt"] = r'''
package com.clipperzero.app.data

import android.content.Context
import com.clipperzero.app.domain.model.AiConfig
import com.clipperzero.app.domain.model.AiProviderPreset
import com.clipperzero.app.domain.model.ScanHistoryItem
import com.clipperzero.app.domain.model.StorageConfig
import com.clipperzero.app.domain.model.StoragePreset
import org.json.JSONArray
import org.json.JSONObject

class PreferencesStore(context: Context) {

    private val prefs = context.getSharedPreferences("clipper_zero_prefs", Context.MODE_PRIVATE)

    fun loadAiConfig(): AiConfig {
        val presetName = prefs.getString("ai_preset", AiProviderPreset.DEEPSEEK.name)
        val preset = runCatching { AiProviderPreset.valueOf(presetName ?: "") }
            .getOrDefault(AiProviderPreset.DEEPSEEK)
        return AiConfig(
            preset = preset,
            baseUrl = prefs.getString("ai_base_url", preset.defaultBaseUrl) ?: preset.defaultBaseUrl,
            primaryKey = prefs.getString("ai_primary_key", "") ?: "",
            backupKey = prefs.getString("ai_backup_key", "") ?: "",
            model = prefs.getString("ai_model", preset.defaultModels.first()) ?: preset.defaultModels.first(),
            offlineMode = prefs.getBoolean("ai_offline_mode", false),
            isConnected = prefs.getBoolean("ai_connected", false),
            lastStatusMessage = prefs.getString("ai_status_msg", "Not connected") ?: "Not connected"
        )
    }

    fun saveAiConfig(config: AiConfig) {
        prefs.edit()
            .putString("ai_preset", config.preset.name)
            .putString("ai_base_url", config.baseUrl)
            .putString("ai_primary_key", config.primaryKey)
            .putString("ai_backup_key", config.backupKey)
            .putString("ai_model", config.model)
            .putBoolean("ai_offline_mode", config.offlineMode)
            .putBoolean("ai_connected", config.isConnected)
            .putString("ai_status_msg", config.lastStatusMessage)
            .apply()
    }

    fun loadStorageConfig(): StorageConfig {
        val presetName = prefs.getString("storage_preset", StoragePreset.MOVIES.name)
        val preset = runCatching { StoragePreset.valueOf(presetName ?: "") }
            .getOrDefault(StoragePreset.MOVIES)
        return StorageConfig(
            preset = preset,
            safTreeUri = prefs.getString("storage_saf_uri", null),
            safDisplayName = prefs.getString("storage_saf_name", null)
        )
    }

    fun saveStorageConfig(config: StorageConfig) {
        prefs.edit()
            .putString("storage_preset", config.preset.name)
            .putString("storage_saf_uri", config.safTreeUri)
            .putString("storage_saf_name", config.safDisplayName)
            .apply()
    }

    fun getLastYtDlpUpdateMs(): Long = prefs.getLong("ytdlp_last_update_ms", 0L)

    fun setLastYtDlpUpdateMs(ms: Long) {
        prefs.edit().putLong("ytdlp_last_update_ms", ms).apply()
    }

    fun loadScanHistory(): List<ScanHistoryItem> {
        val raw = prefs.getString("scan_history_json", null) ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            val list = mutableListOf<ScanHistoryItem>()
            for (i in 0 until arr.length()) {
                val o = arr.optJSONObject(i) ?: continue
                list.add(
                    ScanHistoryItem(
                        url = o.optString("url"),
                        title = o.optString("title"),
                        uploader = o.optString("uploader"),
                        durationSec = o.optDouble("durationSec", 0.0),
                        clipCount = o.optInt("clipCount", 0),
                        scannedAtMs = o.optLong("scannedAtMs", 0L)
                    )
                )
            }
            list
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun addScanHistory(item: ScanHistoryItem): List<ScanHistoryItem> {
        val existing = loadScanHistory().filterNot { it.url == item.url }
        val updated = (listOf(item) + existing).take(20)
        val arr = JSONArray()
        for (entry in updated) {
            arr.put(
                JSONObject()
                    .put("url", entry.url)
                    .put("title", entry.title)
                    .put("uploader", entry.uploader)
                    .put("durationSec", entry.durationSec)
                    .put("clipCount", entry.clipCount)
                    .put("scannedAtMs", entry.scannedAtMs)
            )
        }
        prefs.edit().putString("scan_history_json", arr.toString()).apply()
        return updated
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/data/AiClient.kt"] = r'''
package com.clipperzero.app.data

import com.clipperzero.app.domain.model.AiConfig
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.domain.model.VideoMetadata
import com.clipperzero.app.domain.model.ViralCopy
import com.clipperzero.app.util.ErrorSanitizer
import com.clipperzero.app.util.JsonUtils
import com.clipperzero.app.util.TimeFormatters
import com.clipperzero.app.util.UrlNormalizer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AiClient {

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun testConnection(config: AiConfig): AppResult<String> = withContext(Dispatchers.IO) {
        if (config.offlineMode) {
            return@withContext AppResult.Success("Offline No-AI mode active")
        }
        val base = UrlNormalizer.normalizeAiBaseUrl(config.baseUrl)
        if (base.isBlank()) {
            return@withContext AppResult.Error("Base URL is required")
        }
        val keys = listOf(config.primaryKey.trim(), config.backupKey.trim()).filter { it.isNotEmpty() }
        if (keys.isEmpty()) {
            return@withContext AppResult.Error("Enter an API key or enable Offline No-AI mode")
        }

        val payload = JSONObject()
            .put("model", config.model.trim())
            .put("max_tokens", 16)
            .put(
                "messages",
                JSONArray().put(
                    JSONObject()
                        .put("role", "user")
                        .put("content", "Reply with OK")
                )
            )

        when (val res = executeWithFailover(base, keys, payload)) {
            is AppResult.Success -> AppResult.Success("Connected (${config.model})")
            is AppResult.Error -> res
        }
    }

    suspend fun fetchModels(config: AiConfig): AppResult<List<String>> = withContext(Dispatchers.IO) {
        val base = UrlNormalizer.normalizeAiBaseUrl(config.baseUrl)
        val keys = listOf(config.primaryKey.trim(), config.backupKey.trim()).filter { it.isNotEmpty() }
        if (base.isBlank() || keys.isEmpty()) {
            return@withContext AppResult.Success(config.preset.defaultModels)
        }

        var lastError = "Failed to fetch models"
        for (key in keys) {
            val req = Request.Builder()
                .url("$base/models")
                .header("Authorization", "Bearer $key")
                .get()
                .build()
            try {
                httpClient.newCall(req).execute().use { resp ->
                    val body = resp.body?.string().orEmpty()
                    if (resp.isSuccessful) {
                        val json = JsonUtils.extractStrictJsonObject(body)
                        val data = json?.optJSONArray("data")
                        if (data != null) {
                            val ids = mutableListOf<String>()
                            for (i in 0 until data.length()) {
                                val id = data.optJSONObject(i)?.optString("id").orEmpty()
                                if (id.isNotBlank()) ids.add(id)
                            }
                            if (ids.isNotEmpty()) {
                                return@withContext AppResult.Success(ids.sorted())
                            }
                        }
                        return@withContext AppResult.Success(config.preset.defaultModels)
                    } else if (!shouldFailover(resp.code)) {
                        return@withContext AppResult.Error("HTTP ${resp.code}: ${ErrorSanitizer.sanitize(body)}")
                    } else {
                        lastError = "HTTP ${resp.code}"
                    }
                }
            } catch (e: Exception) {
                lastError = ErrorSanitizer.sanitize(e.message, "Network error")
            }
        }
        AppResult.Error(lastError)
    }

    suspend fun detectAiPicks(
        config: AiConfig,
        video: VideoMetadata
    ): AppResult<List<Signal>> = withContext(Dispatchers.IO) {
        if (config.offlineMode || !config.isConnected || video.transcript.isEmpty()) {
            return@withContext AppResult.Success(emptyList())
        }
        val base = UrlNormalizer.normalizeAiBaseUrl(config.baseUrl)
        val keys = listOf(config.primaryKey.trim(), config.backupKey.trim()).filter { it.isNotEmpty() }
        if (base.isBlank() || keys.isEmpty()) {
            return@withContext AppResult.Success(emptyList())
        }

        val transcriptSummary = buildString {
            val step = (video.transcript.size / 60).coerceAtLeast(1)
            var idx = 0
            while (idx < video.transcript.size && length < 5500) {
                val seg = video.transcript[idx]
                append("[")
                append(seg.startSec.toInt())
                append("s] ")
                append(seg.text.take(120))
                append("\n")
                idx += step
            }
        }

        val prompt = """
            Analyze this video transcript ("${video.title}") and pick up to 5 most viral short-form clip moments (15-55 seconds each).
            Return ONLY strict JSON matching:
            {"picks":[{"start":12.0,"end":42.0,"score":0.9,"reason":"short reason"}]}
            Transcript:
            $transcriptSummary
        """.trimIndent()

        val payload = JSONObject()
            .put("model", config.model)
            .put("max_tokens", 700)
            .put("temperature", 0.3)
            .put(
                "messages",
                JSONArray()
                    .put(JSONObject().put("role", "system").put("content", "Return valid JSON only. No markdown."))
                    .put(JSONObject().put("role", "user").put("content", prompt))
            )

        when (val res = executeWithFailover(base, keys, payload)) {
            is AppResult.Error -> res
            is AppResult.Success -> {
                val json = JsonUtils.extractStrictJsonObject(res.data)
                    ?: return@withContext AppResult.Success(emptyList())
                val picks = json.optJSONArray("picks") ?: return@withContext AppResult.Success(emptyList())
                val signals = mutableListOf<Signal>()
                for (i in 0 until picks.length()) {
                    val item = picks.optJSONObject(i) ?: continue
                    val start = item.optDouble("start", -1.0)
                    val end = item.optDouble("end", -1.0)
                    if (start >= 0.0 && end > start) {
                        val clampedEnd = if (video.durationSec > 0.0) end.coerceAtMost(video.durationSec) else end
                        signals.add(
                            Signal(
                                startSec = start,
                                endSec = clampedEnd,
                                score = item.optDouble("score", 0.85).coerceIn(0.4, 1.0),
                                type = SignalType.AI_PICK,
                                label = item.optString("reason", "AI viral pick")
                            )
                        )
                    }
                }
                AppResult.Success(signals)
            }
        }
    }

    suspend fun generateViralCopy(
        config: AiConfig,
        video: VideoMetadata,
        clip: ClipCandidate
    ): AppResult<ViralCopy> = withContext(Dispatchers.IO) {
        if (config.offlineMode || !config.isConnected) {
            return@withContext AppResult.Error("AI offline")
        }
        val base = UrlNormalizer.normalizeAiBaseUrl(config.baseUrl)
        val keys = listOf(config.primaryKey.trim(), config.backupKey.trim()).filter { it.isNotEmpty() }
        if (base.isBlank() || keys.isEmpty()) {
            return@withContext AppResult.Error("Missing AI key")
        }

        val snippet = video.transcript
            .filter { it.endSec >= clip.startSec && it.startSec <= clip.endSec }
            .joinToString(" ") { it.text }
            .take(900)

        val prompt = """
            Create a viral Shorts/Reels title, 1-sentence hook, and 5 hashtags for this clip.
            Video: ${video.title}
            Window: ${TimeFormatters.formatTimestamp(clip.startSec)} - ${TimeFormatters.formatTimestamp(clip.endSec)}
            Signal: ${clip.reason}
            Transcript: ${snippet.ifBlank { "N/A" }}
            Return ONLY strict JSON:
            {"title":"...","hook":"...","hashtags":["#tag1","#tag2","#tag3","#tag4","#tag5"]}
        """.trimIndent()

        val payload = JSONObject()
            .put("model", config.model)
            .put("max_tokens", 280)
            .put("temperature", 0.7)
            .put(
                "messages",
                JSONArray()
                    .put(JSONObject().put("role", "system").put("content", "Return valid JSON only. No markdown."))
                    .put(JSONObject().put("role", "user").put("content", prompt))
            )

        when (val res = executeWithFailover(base, keys, payload)) {
            is AppResult.Error -> res
            is AppResult.Success -> {
                val json = JsonUtils.extractStrictJsonObject(res.data)
                    ?: return@withContext AppResult.Error("Invalid JSON from AI")
                val title = json.optString("title").trim()
                val hook = json.optString("hook").trim()
                val tagsArr = json.optJSONArray("hashtags")
                val tags = mutableListOf<String>()
                if (tagsArr != null) {
                    for (i in 0 until tagsArr.length()) {
                        val t = tagsArr.optString(i).trim()
                        if (t.isNotBlank()) tags.add(if (t.startsWith("#")) t else "#$t")
                    }
                }
                if (title.isBlank()) return@withContext AppResult.Error("Empty AI title")
                AppResult.Success(ViralCopy(title, hook, tags.ifEmpty { listOf("#shorts", "#clips", "#viral") }))
            }
        }
    }

    private fun executeWithFailover(
        baseUrl: String,
        keys: List<String>,
        payload: JSONObject
    ): AppResult<String> {
        var lastError = "AI request failed"
        for ((index, key) in keys.withIndex()) {
            val req = Request.Builder()
                .url("$baseUrl/chat/completions")
                .header("Authorization", "Bearer $key")
                .header("Content-Type", "application/json")
                .post(payload.toString().toRequestBody(jsonMediaType))
                .build()
            try {
                httpClient.newCall(req).execute().use { resp ->
                    val rawBody = resp.body?.string().orEmpty()
                    if (resp.isSuccessful) {
                        val root = JsonUtils.extractStrictJsonObject(rawBody)
                        val content = root
                            ?.optJSONArray("choices")
                            ?.optJSONObject(0)
                            ?.optJSONObject("message")
                            ?.optString("content")
                            .orEmpty()
                        return if (content.isNotBlank()) {
                            AppResult.Success(content)
                        } else {
                            AppResult.Error("Empty response from model")
                        }
                    } else {
                        val code = resp.code
                        lastError = "HTTP $code: ${ErrorSanitizer.sanitize(rawBody)}"
                        if (shouldFailover(code) && index < keys.lastIndex) {
                            return@use
                        }
                        return AppResult.Error(lastError)
                    }
                }
            } catch (e: Exception) {
                lastError = ErrorSanitizer.sanitize(e.message, "Network error")
                if (index < keys.lastIndex) continue
                return AppResult.Error(lastError, e)
            }
        }
        return AppResult.Error(lastError)
    }

    private fun shouldFailover(code: Int): Boolean {
        return code == 401 || code == 402 || code == 403 || code == 429 || code in 500..599
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/data/YtDlpRepository.kt"] = r'''
package com.clipperzero.app.data

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.provider.OpenableColumns
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.domain.model.HeatmapPoint
import com.clipperzero.app.domain.model.SourceKind
import com.clipperzero.app.domain.model.TranscriptSegment
import com.clipperzero.app.domain.model.VideoMetadata
import com.clipperzero.app.util.ErrorSanitizer
import com.clipperzero.app.util.TimeFormatters
import com.clipperzero.app.util.UrlNormalizer
import com.yausername.aria2c.Aria2c
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

class YtDlpRepository(
    private val context: Context,
    private val prefs: PreferencesStore
) {
    @Volatile
    private var initialized = false

    val cookiesFile: File
        get() = File(context.filesDir, "yt_cookies.txt")

    fun hasCookies(): Boolean = cookiesFile.exists() && cookiesFile.length() > 0L

    fun importCookies(uri: Uri): AppResult<String> {
        return try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(cookiesFile).use { output ->
                    input.copyTo(output)
                }
            } ?: return AppResult.Error("Unable to read selected cookies file")
            AppResult.Success("Cookies imported (${cookiesFile.length()} bytes)")
        } catch (e: Exception) {
            AppResult.Error(ErrorSanitizer.sanitize(e.message, "Cookie import failed"), e)
        }
    }

    fun clearCookies() {
        if (cookiesFile.exists()) cookiesFile.delete()
    }

    suspend fun ensureInitialized() = withContext(Dispatchers.IO) {
        if (initialized) return@withContext
        synchronized(this) {
            if (initialized) return@synchronized
            YoutubeDL.getInstance().init(context)
            FFmpeg.getInstance().init(context)
            Aria2c.getInstance().init(context)
            initialized = true
        }
    }

    suspend fun autoUpdateIfDue(): String? = withContext(Dispatchers.IO) {
        val last = prefs.getLastYtDlpUpdateMs()
        val now = System.currentTimeMillis()
        if (now - last < 24L * 60L * 60L * 1000L) return@withContext null
        when (val res = updateYtDlp()) {
            is AppResult.Success -> res.data
            is AppResult.Error -> null
        }
    }

    suspend fun updateYtDlp(): AppResult<String> = withContext(Dispatchers.IO) {
        try {
            ensureInitialized()
            val status = YoutubeDL.getInstance().updateYoutubeDL(context)
            prefs.setLastYtDlpUpdateMs(System.currentTimeMillis())
            val msg = when (status) {
                YoutubeDL.UpdateStatus.DONE -> "yt-dlp updated"
                YoutubeDL.UpdateStatus.ALREADY_UP_TO_DATE -> "yt-dlp is up to date"
                else -> "yt-dlp update checked"
            }
            AppResult.Success(msg)
        } catch (e: Exception) {
            AppResult.Error(ErrorSanitizer.sanitize(e.message, "yt-dlp update failed"), e)
        }
    }

    suspend fun scanSource(
        rawInput: String,
        fetchLiveChat: Boolean,
        onStatus: (String) -> Unit
    ): AppResult<VideoMetadata> = withContext(Dispatchers.IO) {
        val (normalized, kind) = UrlNormalizer.normalize(rawInput)
        if (kind == SourceKind.LOCAL) {
            return@withContext scanLocalVideo(normalized)
        }

        try {
            ensureInitialized()
        } catch (e: Exception) {
            return@withContext AppResult.Error(ErrorSanitizer.sanitize(e.message, "Engine init failed"), e)
        }

        val workDir = File(context.cacheDir, "scan_${UUID.randomUUID().toString().take(8)}")
        workDir.mkdirs()

        val clientProfiles = if (kind == SourceKind.YOUTUBE) {
            listOf(
                "tv_embedded,mweb" to "youtube:player_client=tv_embedded,mweb",
                "ios,web" to "youtube:player_client=ios,web",
                "default" to null
            )
        } else {
            listOf("default" to null)
        }

        var lastError = "Unable to fetch video metadata"
        for ((label, extractorArg) in clientProfiles) {
            onStatus("Scanning metadata ($label)...")
            val req = YoutubeDLRequest(normalized)
            req.addOption("--skip-download")
            req.addOption("--write-info-json")
            req.addOption("--no-playlist")
            req.addOption("--write-auto-subs")
            req.addOption("--write-subs")
            req.addOption("--sub-langs", "en,hi,bn,es,ar")
            req.addOption("--sub-format", "vtt")
            req.addOption("-o", File(workDir, "video.%(ext)s").absolutePath)
            if (extractorArg != null) {
                req.addOption("--extractor-args", extractorArg)
            }
            if (hasCookies()) {
                req.addOption("--cookies", cookiesFile.absolutePath)
            }

            try {
                YoutubeDL.getInstance().execute(req, "scan_${label}") { _, _, _ -> }
                val infoFile = workDir.listFiles()?.firstOrNull { it.name.endsWith(".info.json") }
                if (infoFile != null && infoFile.exists()) {
                    val infoJson = JSONObject(infoFile.readText())
                    val isLiveVod = infoJson.optBoolean("was_live", false) ||
                        infoJson.optBoolean("is_live", false) ||
                        infoJson.optString("live_status", "") == "was_live"

                    var liveChatPath: String? = null
                    if (kind == SourceKind.YOUTUBE && (fetchLiveChat || isLiveVod)) {
                        onStatus("Fetching live chat replay...")
                        liveChatPath = fetchLiveChatOnly(normalized, workDir, extractorArg)
                    }

                    val metadata = parseInfoJson(
                        infoJson = infoJson,
                        sourceUrl = rawInput,
                        normalizedUrl = normalized,
                        kind = kind,
                        workDir = workDir,
                        liveChatPath = liveChatPath
                    )
                    return@withContext AppResult.Success(metadata)
                }
            } catch (e: Exception) {
                lastError = ErrorSanitizer.sanitize(e.message, "Scan failed on $label")
            }
        }
        AppResult.Error(lastError)
    }

    private fun fetchLiveChatOnly(
        normalizedUrl: String,
        workDir: File,
        extractorArg: String?
    ): String? {
        return try {
            val req = YoutubeDLRequest(normalizedUrl)
            req.addOption("--skip-download")
            req.addOption("--write-subs")
            req.addOption("--sub-langs", "live_chat")
            req.addOption("--no-playlist")
            req.addOption("-o", File(workDir, "chat.%(ext)s").absolutePath)
            if (extractorArg != null) {
                req.addOption("--extractor-args", extractorArg)
            }
            if (hasCookies()) {
                req.addOption("--cookies", cookiesFile.absolutePath)
            }
            YoutubeDL.getInstance().execute(req, "scan_live_chat") { _, _, _ -> }
            workDir.listFiles()?.firstOrNull {
                it.name.contains("live_chat") && it.name.endsWith(".json")
            }?.absolutePath
        } catch (_: Exception) {
            null
        }
    }

    private fun parseInfoJson(
        infoJson: JSONObject,
        sourceUrl: String,
        normalizedUrl: String,
        kind: SourceKind,
        workDir: File,
        liveChatPath: String?
    ): VideoMetadata {
        val id = infoJson.optString("id", UUID.randomUUID().toString().take(8))
        val title = infoJson.optString("title", "Untitled Video")
        val uploader = infoJson.optString("uploader", infoJson.optString("channel", "Unknown"))
        val duration = infoJson.optDouble("duration", 0.0).coerceAtLeast(0.0)
        val isLiveVod = infoJson.optBoolean("was_live", false) ||
            infoJson.optString("live_status", "") == "was_live"

        val heatmap = mutableListOf<HeatmapPoint>()
        val hmArr = infoJson.optJSONArray("heatmap")
        if (hmArr != null) {
            for (i in 0 until hmArr.length()) {
                val pt = hmArr.optJSONObject(i) ?: continue
                heatmap.add(
                    HeatmapPoint(
                        startTime = pt.optDouble("start_time", 0.0),
                        endTime = pt.optDouble("end_time", 0.0),
                        value = pt.optDouble("value", 0.0)
                    )
                )
            }
        }

        val previewUrl = pickPreviewStreamUrl(infoJson)
        val vttFile = workDir.listFiles()?.firstOrNull { it.name.endsWith(".vtt") }
        val transcript = if (vttFile != null) parseVtt(vttFile) else emptyList()

        return VideoMetadata(
            id = id,
            sourceUrl = sourceUrl,
            normalizedUrl = normalizedUrl,
            title = title,
            uploader = uploader,
            durationSec = duration,
            isLiveVod = isLiveVod,
            sourceKind = kind,
            previewStreamUrl = previewUrl,
            heatmap = heatmap,
            transcript = transcript,
            liveChatFilePath = liveChatPath
        )
    }

    private fun pickPreviewStreamUrl(infoJson: JSONObject): String? {
        val formats = infoJson.optJSONArray("formats")
        if (formats != null) {
            var bestMuxed: Pair<Int, String>? = null
            for (i in 0 until formats.length()) {
                val f = formats.optJSONObject(i) ?: continue
                val url = f.optString("url", "")
                if (url.isBlank() || !url.startsWith("http")) continue
                val vcodec = f.optString("vcodec", "none")
                val acodec = f.optString("acodec", "none")
                val ext = f.optString("ext", "")
                val height = f.optInt("height", 0)
                if (vcodec != "none" && acodec != "none" && (ext == "mp4" || ext == "webm")) {
                    val score = if (height in 360..720) 1000 + height else height
                    if (bestMuxed == null || score > bestMuxed.first) {
                        bestMuxed = score to url
                    }
                }
            }
            if (bestMuxed != null) return bestMuxed.second
        }
        val direct = infoJson.optString("url", "")
        return direct.takeIf { it.startsWith("http") }
    }

    private fun parseVtt(file: File): List<TranscriptSegment> {
        val segments = mutableListOf<TranscriptSegment>()
        try {
            val lines = file.readLines(Charsets.UTF_8)
            var i = 0
            while (i < lines.size) {
                val line = lines[i].trim()
                if (line.contains("-->")) {
                    val parts = line.split("-->")
                    if (parts.size >= 2) {
                        val start = TimeFormatters.parseTimeToSeconds(parts[0].trim().split(" ")[0])
                        val end = TimeFormatters.parseTimeToSeconds(parts[1].trim().split(" ")[0])
                        val textBuilder = StringBuilder()
                        i++
                        while (i < lines.size && lines[i].isNotBlank()) {
                            val cleaned = lines[i].replace(Regex("<[^>]+>"), "").trim()
                            if (cleaned.isNotBlank()) {
                                if (textBuilder.isNotEmpty()) textBuilder.append(" ")
                                textBuilder.append(cleaned)
                            }
                            i++
                        }
                        val text = textBuilder.toString().trim()
                        if (start != null && end != null && text.isNotBlank()) {
                            if (segments.lastOrNull()?.text != text) {
                                segments.add(TranscriptSegment(start, end, text))
                            }
                        }
                        continue
                    }
                }
                i++
            }
        } catch (_: Exception) {
        }
        return segments
    }

    private fun scanLocalVideo(uriString: String): AppResult<VideoMetadata> {
        return try {
            val uri = Uri.parse(uriString)
            val retriever = MediaMetadataRetriever()
            retriever.setDataSource(context, uri)
            val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
                ?.toLongOrNull() ?: 0L
            retriever.release()

            var displayName = "Local Video"
            context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0 && cursor.moveToFirst()) {
                    displayName = cursor.getString(idx) ?: displayName
                }
            }

            AppResult.Success(
                VideoMetadata(
                    id = UUID.randomUUID().toString().take(8),
                    sourceUrl = uriString,
                    normalizedUrl = uriString,
                    title = displayName,
                    uploader = "Local Device",
                    durationSec = (durationMs / 1000.0).coerceAtLeast(1.0),
                    isLiveVod = false,
                    sourceKind = SourceKind.LOCAL,
                    previewStreamUrl = uriString,
                    heatmap = emptyList(),
                    transcript = emptyList(),
                    liveChatFilePath = null,
                    localUri = uriString
                )
            )
        } catch (e: Exception) {
            AppResult.Error(ErrorSanitizer.sanitize(e.message, "Failed to read local video"), e)
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/data/StorageManager.kt"] = r'''
package com.clipperzero.app.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import androidx.documentfile.provider.DocumentFile
import com.clipperzero.app.domain.model.StorageConfig
import com.clipperzero.app.domain.model.StoragePreset
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

data class SavedMediaResult(
    val uriString: String,
    val displayPath: String
)

class StorageManager(
    private val context: Context,
    private val prefs: PreferencesStore
) {

    fun sanitizeFileName(raw: String): String {
        val cleaned = raw.replace(Regex("[^A-Za-z0-9._ -]"), "_")
            .replace(Regex("\\s+"), "_")
            .trim('_')
            .take(56)
        return cleaned.ifBlank { "clip_${System.currentTimeMillis()}" }
    }

    fun saveVideo(sourceFile: File, baseName: String): SavedMediaResult {
        val config = prefs.loadStorageConfig()
        val safeName = "${sanitizeFileName(baseName)}.mp4"

        if (config.preset == StoragePreset.CUSTOM_SAF && !config.safTreeUri.isNullOrBlank()) {
            saveViaSaf(sourceFile, config.safTreeUri, safeName, "video/mp4")?.let { return it }
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            saveViaMediaStore(sourceFile, safeName, config)?.let { return it }
        }

        return saveToAppExternalFallback(sourceFile, safeName)
    }

    fun saveSidecarTxt(content: String, baseName: String): String? {
        val config = prefs.loadStorageConfig()
        val safeName = "${sanitizeFileName(baseName)}.txt"
        val tempTxt = File(context.cacheDir, safeName)
        tempTxt.writeText(content, Charsets.UTF_8)

        return try {
            if (config.preset == StoragePreset.CUSTOM_SAF && !config.safTreeUri.isNullOrBlank()) {
                saveViaSaf(tempTxt, config.safTreeUri, safeName, "text/plain")?.displayPath
            } else {
                val outDir = File(context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS), "ClipPulse")
                outDir.mkdirs()
                val dst = File(outDir, safeName)
                tempTxt.copyTo(dst, overwrite = true)
                dst.absolutePath
            }
        } catch (_: Exception) {
            null
        } finally {
            tempTxt.delete()
        }
    }

    private fun saveViaSaf(
        sourceFile: File,
        treeUriStr: String,
        fileName: String,
        mimeType: String
    ): SavedMediaResult? {
        return try {
            val treeUri = Uri.parse(treeUriStr)
            val dir = DocumentFile.fromTreeUri(context, treeUri) ?: return null
            val doc = dir.createFile(mimeType, fileName) ?: return null
            context.contentResolver.openOutputStream(doc.uri)?.use { out ->
                FileInputStream(sourceFile).use { input ->
                    input.copyTo(out)
                }
            } ?: return null
            SavedMediaResult(doc.uri.toString(), "${dir.name ?: "Custom"}/$fileName")
        } catch (_: Exception) {
            null
        }
    }

    private fun saveViaMediaStore(
        sourceFile: File,
        fileName: String,
        config: StorageConfig
    ): SavedMediaResult? {
        return try {
            val relativePath = when (config.preset) {
                StoragePreset.MOVIES -> "${Environment.DIRECTORY_MOVIES}/ClipPulse"
                StoragePreset.DOWNLOADS -> "${Environment.DIRECTORY_DOWNLOADS}/ClipPulse"
                StoragePreset.DCIM -> "${Environment.DIRECTORY_DCIM}/ClipPulse"
                StoragePreset.CUSTOM_SAF -> "${Environment.DIRECTORY_MOVIES}/ClipPulse"
            }

            val collection = if (config.preset == StoragePreset.DOWNLOADS && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                MediaStore.Downloads.EXTERNAL_CONTENT_URI
            } else {
                MediaStore.Video.Media.EXTERNAL_CONTENT_URI
            }

            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }
            }

            val resolver = context.contentResolver
            val uri = resolver.insert(collection, values) ?: return null
            resolver.openOutputStream(uri)?.use { out ->
                FileInputStream(sourceFile).use { input ->
                    input.copyTo(out)
                }
            } ?: return null

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val done = ContentValues().apply {
                    put(MediaStore.MediaColumns.IS_PENDING, 0)
                }
                resolver.update(uri, done, null, null)
            }
            SavedMediaResult(uri.toString(), "$relativePath/$fileName")
        } catch (_: Exception) {
            null
        }
    }

    private fun saveToAppExternalFallback(sourceFile: File, fileName: String): SavedMediaResult {
        val dir = File(context.getExternalFilesDir(Environment.DIRECTORY_MOVIES), "ClipPulse")
        dir.mkdirs()
        val dst = File(dir, fileName)
        FileInputStream(sourceFile).use { input ->
            FileOutputStream(dst).use { out ->
                input.copyTo(out)
            }
        }
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            dst
        )
        return SavedMediaResult(uri.toString(), dst.absolutePath)
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/data/ExportRepository.kt"] = r'''
package com.clipperzero.app.data

import android.content.Context
import android.net.Uri
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.domain.model.ExportJob
import com.clipperzero.app.util.ErrorSanitizer
import com.clipperzero.app.util.FfmpegRunner
import com.clipperzero.app.util.SuperChatOverlayRenderer
import com.clipperzero.app.util.TimeFormatters
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

class ExportRepository(
    private val context: Context,
    private val ytDlpRepository: YtDlpRepository,
    private val ffmpegRunner: FfmpegRunner,
    private val storageManager: StorageManager
) {
    @Volatile
    private var activeProcessId: String? = null

    fun cancelActiveExport() {
        activeProcessId?.let { id ->
            runCatching { YoutubeDL.getInstance().destroyProcessById(id) }
        }
        ffmpegRunner.cancelCurrent()
    }

    suspend fun runExport(
        job: ExportJob,
        onProgress: (Float, String) -> Unit
    ): AppResult<SavedMediaResult> = withContext(Dispatchers.IO) {
        val workDir = File(context.cacheDir, "export_${job.id.take(8)}")
        workDir.mkdirs()

        try {
            ytDlpRepository.ensureInitialized()
            onProgress(0.05f, "Preparing clip segment...")

            val rawSegmentFile = if (!job.localUri.isNullOrBlank()) {
                extractLocalSegment(job, workDir, onProgress)
            } else {
                downloadRemoteSection(job, workDir, onProgress)
            }

            if (rawSegmentFile == null || !rawSegmentFile.exists() || rawSegmentFile.length() == 0L) {
                return@withContext AppResult.Error("Failed to extract video segment")
            }

            val needsPostProcess = !job.options.fastCut ||
                job.options.cropVertical916 ||
                (job.options.superChatOverlay && job.superChat != null) ||
                job.options.audioLoudnorm

            val finalVideoFile = if (!needsPostProcess) {
                onProgress(0.85f, "Fast-cut ready, saving...")
                rawSegmentFile
            } else {
                onProgress(0.58f, "Rendering filters with FFmpeg...")
                postProcessWithFfmpeg(job, rawSegmentFile, workDir, onProgress)
            }

            if (!finalVideoFile.exists() || finalVideoFile.length() == 0L) {
                return@withContext AppResult.Error("Processed output file is empty")
            }

            onProgress(0.92f, "Saving to storage...")
            val baseName = "${job.title}_${TimeFormatters.formatTimestamp(job.startSec).replace(":", "-")}"
            val saved = storageManager.saveVideo(finalVideoFile, baseName)

            if (job.options.writeSidecarTxt) {
                val txtBody = buildSidecarText(job)
                storageManager.saveSidecarTxt(txtBody, baseName)
            }

            onProgress(1.0f, "Export complete")
            AppResult.Success(saved)
        } catch (e: Exception) {
            AppResult.Error(ErrorSanitizer.sanitize(e.message, "Export failed"), e)
        } finally {
            workDir.deleteRecursively()
        }
    }

    private suspend fun extractLocalSegment(
        job: ExportJob,
        workDir: File,
        onProgress: (Float, String) -> Unit
    ): File? {
        val uri = Uri.parse(job.localUri!!)
        val localCopy = File(workDir, "local_input.mp4")
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(localCopy).use { out ->
                input.copyTo(out)
            }
        } ?: return null

        val outFile = File(workDir, "segment.mp4")
        val duration = (job.endSec - job.startSec).coerceAtLeast(1.0)
        onProgress(0.30f, "Cutting local video...")
        val args = listOf(
            "-y",
            "-ss", TimeFormatters.formatFfmpegTime(job.startSec),
            "-i", localCopy.absolutePath,
            "-t", String.format(Locale.US, "%.2f", duration),
            "-c", "copy",
            "-movflags", "+faststart",
            outFile.absolutePath
        )
        val res = ffmpegRunner.run(args)
        return if (res.isSuccess && outFile.exists()) outFile else null
    }

    private fun downloadRemoteSection(
        job: ExportJob,
        workDir: File,
        onProgress: (Float, String) -> Unit
    ): File? {
        val sectionArg = TimeFormatters.formatSectionRange(job.startSec, job.endSec)
        val outTemplate = File(workDir, "clip.%(ext)s").absolutePath
        val processId = "export_${job.id}"
        activeProcessId = processId

        val attempts = listOf(false, true)
        for (useAria2c in attempts) {
            val req = YoutubeDLRequest(job.sourceUrl)
            req.addOption("--download-sections", sectionArg)
            req.addOption("-N", "8")
            req.addOption("--no-playlist")
            req.addOption("-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best")
            req.addOption("--merge-output-format", "mp4")
            req.addOption("-o", outTemplate)
            if (ytDlpRepository.hasCookies()) {
                req.addOption("--cookies", ytDlpRepository.cookiesFile.absolutePath)
            }
            if (useAria2c) {
                req.addOption("--downloader", "libaria2c.so")
                req.addOption("--external-downloader-args", "aria2c:'--summary-interval=1 -x 8 -s 8 -k 1M'")
            }

            try {
                onProgress(0.15f, if (useAria2c) "Downloading section (aria2c fallback)..." else "Downloading clip section...")
                YoutubeDL.getInstance().execute(req, processId) { progress, _, _ ->
                    if (progress >= 0f) {
                        val scaled = (0.15f + (progress / 100f) * 0.40f).coerceIn(0.15f, 0.55f)
                        onProgress(scaled, "Downloading ${progress.toInt()}%...")
                    }
                }
                val file = workDir.listFiles()?.firstOrNull {
                    it.isFile && (it.name.endsWith(".mp4") || it.name.endsWith(".mkv") || it.name.endsWith(".webm"))
                }
                if (file != null && file.length() > 0L) {
                    activeProcessId = null
                    return file
                }
            } catch (_: Exception) {
                if (useAria2c) {
                    activeProcessId = null
                    return null
                }
            }
        }
        activeProcessId = null
        return null
    }

    private suspend fun postProcessWithFfmpeg(
        job: ExportJob,
        inputFile: File,
        workDir: File,
        onProgress: (Float, String) -> Unit
    ): File {
        val outputFile = File(workDir, "final_clip.mp4")
        val overlayFile = if (job.options.superChatOverlay && job.superChat != null) {
            SuperChatOverlayRenderer.renderToPng(job.superChat, File(workDir, "sc_overlay.png"))
        } else {
            null
        }

        val args = buildFfmpegArgs(
            inputFile = inputFile,
            outputFile = outputFile,
            overlayFile = overlayFile,
            crop916 = job.options.cropVertical916,
            cropOffsetX = job.options.cropOffsetX,
            useLoudnorm = job.options.audioLoudnorm
        )

        val res = ffmpegRunner.run(args) { line ->
            if (line.contains("time=")) {
                onProgress(0.76f, "Encoding clip...")
            }
        }

        if (res.isSuccess && outputFile.exists() && outputFile.length() > 0L) {
            return outputFile
        }

        if (job.options.audioLoudnorm) {
            onProgress(0.72f, "Retrying audio without loudnorm...")
            val fallbackArgs = buildFfmpegArgs(
                inputFile = inputFile,
                outputFile = outputFile,
                overlayFile = overlayFile,
                crop916 = job.options.cropVertical916,
                cropOffsetX = job.options.cropOffsetX,
                useLoudnorm = false
            )
            val fallbackRes = ffmpegRunner.run(fallbackArgs)
            if (fallbackRes.isSuccess && outputFile.exists() && outputFile.length() > 0L) {
                return outputFile
            }
        }

        return inputFile
    }

    private fun buildFfmpegArgs(
        inputFile: File,
        outputFile: File,
        overlayFile: File?,
        crop916: Boolean,
        cropOffsetX: Float,
        useLoudnorm: Boolean
    ): List<String> {
        val args = mutableListOf("-y", "-i", inputFile.absolutePath)
        if (overlayFile != null) {
            args.add("-i")
            args.add(overlayFile.absolutePath)
        }

        val offsetStr = String.format(Locale.US, "%.3f", cropOffsetX.coerceIn(0f, 1f))
        val cropExpr = "crop='min(iw,ih*9/16)':ih:'(iw-min(iw,ih*9/16))*$offsetStr':0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

        if (overlayFile != null) {
            val baseChain = if (crop916) "[0:v]$cropExpr[vbase]" else "[0:v]null[vbase]"
            val filterComplex = "$baseChain;[1:v]scale=iw*0.85:-1[ovr];[vbase][ovr]overlay=(W-w)/2:H-h-96[vout]"
            args.addAll(listOf("-filter_complex", filterComplex, "-map", "[vout]", "-map", "0:a?"))
        } else if (crop916) {
            args.addAll(listOf("-vf", cropExpr))
        }

        args.addAll(listOf("-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"))

        if (useLoudnorm) {
            args.addAll(listOf("-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k"))
        } else {
            args.addAll(listOf("-c:a", "aac", "-b:a", "160k"))
        }

        args.addAll(listOf("-movflags", "+faststart", outputFile.absolutePath))
        return args
    }

    private fun buildSidecarText(job: ExportJob): String {
        return buildString {
            appendLine("TITLE: ${job.viralCopy?.title ?: job.title}")
            appendLine("WINDOW: ${TimeFormatters.formatTimestamp(job.startSec)} - ${TimeFormatters.formatTimestamp(job.endSec)}")
            appendLine("SOURCE: ${job.sourceUrl}")
            if (job.viralCopy != null) {
                appendLine()
                appendLine("HOOK:")
                appendLine(job.viralCopy.hook)
                appendLine()
                appendLine("HASHTAGS:")
                appendLine(job.viralCopy.hashtags.joinToString(" "))
            }
            if (job.superChat != null) {
                appendLine()
                appendLine("SUPER CHAT: ${job.superChat.amountDisplay} - ${job.superChat.author}")
                appendLine(job.superChat.message)
            }
        }
    }
}
'''

# ---------- SERVICE & DI ----------

FILES["app/src/main/java/com/clipperzero/app/service/ExportForegroundService.kt"] = r'''
package com.clipperzero.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.clipperzero.app.ClipperZeroApp
import com.clipperzero.app.MainActivity
import com.clipperzero.app.R
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.domain.model.ExportJob
import com.clipperzero.app.domain.model.ExportStatus
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

object ExportQueueState {
    private val _jobs = MutableStateFlow<List<ExportJob>>(emptyList())
    val jobs: StateFlow<List<ExportJob>> = _jobs.asStateFlow()

    fun enqueue(job: ExportJob) {
        _jobs.update { listOf(job) + it }
    }

    fun updateJob(jobId: String, transform: (ExportJob) -> ExportJob) {
        _jobs.update { list ->
            list.map { if (it.id == jobId) transform(it) else it }
        }
    }

    fun nextQueued(): ExportJob? {
        return _jobs.value.lastOrNull { it.status == ExportStatus.QUEUED }
    }

    fun clearCompleted() {
        _jobs.update { list ->
            list.filter { it.status == ExportStatus.QUEUED || it.status == ExportStatus.RUNNING }
        }
    }
}

class ExportForegroundService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var workerJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_CANCEL) {
            val targetId = intent.getStringExtra(EXTRA_JOB_ID)
            val container = (application as ClipperZeroApp).container
            container.exportRepository.cancelActiveExport()
            if (targetId != null) {
                ExportQueueState.updateJob(targetId) {
                    it.copy(status = ExportStatus.CANCELLED, stage = "Cancelled")
                }
            }
            workerJob?.cancel()
            workerJob = null
            startWorkerIfNeeded()
            return START_NOT_STICKY
        }

        startForeground(NOTIFICATION_ID, buildNotification("Exporting clip...", 0))
        startWorkerIfNeeded()
        return START_NOT_STICKY
    }

    private fun startWorkerIfNeeded() {
        if (workerJob?.isActive == true) return
        val container = (application as ClipperZeroApp).container
        workerJob = scope.launch {
            while (true) {
                val next = ExportQueueState.nextQueued() ?: break
                ExportQueueState.updateJob(next.id) {
                    it.copy(status = ExportStatus.RUNNING, progress = 0.02f, stage = "Starting...")
                }
                updateNotification("Exporting: ${next.title.take(32)}", 5)

                val result = container.exportRepository.runExport(next) { progress, stage ->
                    ExportQueueState.updateJob(next.id) {
                        it.copy(progress = progress, stage = stage)
                    }
                    updateNotification(stage, (progress * 100f).toInt())
                }

                when (result) {
                    is AppResult.Success -> {
                        ExportQueueState.updateJob(next.id) {
                            it.copy(
                                status = ExportStatus.COMPLETED,
                                progress = 1f,
                                stage = "Saved: ${result.data.displayPath}",
                                outputUri = result.data.uriString,
                                outputPath = result.data.displayPath
                            )
                        }
                    }
                    is AppResult.Error -> {
                        ExportQueueState.updateJob(next.id) {
                            if (it.status == ExportStatus.CANCELLED) it
                            else it.copy(
                                status = ExportStatus.FAILED,
                                stage = "Failed",
                                errorMessage = result.message
                            )
                        }
                    }
                }
            }
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Clip Exports",
                NotificationManager.IMPORTANCE_LOW
            )
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(channel)
        }
    }

    private fun updateNotification(text: String, progress: Int) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIFICATION_ID, buildNotification(text, progress))
    }

    private fun buildNotification(text: String, progress: Int): Notification {
        val openIntent = Intent(this, MainActivity::class.java)
        val openPi = PendingIntent.getActivity(
            this,
            0,
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val cancelIntent = Intent(this, ExportForegroundService::class.java).apply {
            action = ACTION_CANCEL
        }
        val cancelPi = PendingIntent.getService(
            this,
            1,
            cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Clipper Zero")
            .setContentText(text)
            .setProgress(100, progress.coerceIn(0, 100), progress <= 0)
            .setOngoing(true)
            .setContentIntent(openPi)
            .addAction(0, "Cancel", cancelPi)
            .build()
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        const val CHANNEL_ID = "clipper_zero_export"
        const val NOTIFICATION_ID = 4102
        const val ACTION_START = "com.clipperzero.app.ACTION_START_EXPORT"
        const val ACTION_CANCEL = "com.clipperzero.app.ACTION_CANCEL_EXPORT"
        const val EXTRA_JOB_ID = "extra_job_id"

        fun start(context: Context) {
            val intent = Intent(context, ExportForegroundService::class.java).apply {
                action = ACTION_START
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun cancel(context: Context, jobId: String) {
            val intent = Intent(context, ExportForegroundService::class.java).apply {
                action = ACTION_CANCEL
                putExtra(EXTRA_JOB_ID, jobId)
            }
            context.startService(intent)
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/AppContainer.kt"] = r'''
package com.clipperzero.app

import android.content.Context
import com.clipperzero.app.data.AiClient
import com.clipperzero.app.data.ExportRepository
import com.clipperzero.app.data.PreferencesStore
import com.clipperzero.app.data.StorageManager
import com.clipperzero.app.data.YtDlpRepository
import com.clipperzero.app.domain.engine.ChatVelocityEngine
import com.clipperzero.app.domain.engine.ConsensusMerger
import com.clipperzero.app.domain.engine.HeatmapEngine
import com.clipperzero.app.domain.engine.SuperChatEngine
import com.clipperzero.app.domain.engine.TranscriptExcitementEngine
import com.clipperzero.app.util.FfmpegRunner

class AppContainer(val appContext: Context) {
    val prefs = PreferencesStore(appContext)
    val aiClient = AiClient()
    val ffmpegRunner = FfmpegRunner(appContext)
    val ytDlpRepository = YtDlpRepository(appContext, prefs)
    val storageManager = StorageManager(appContext, prefs)
    val exportRepository = ExportRepository(appContext, ytDlpRepository, ffmpegRunner, storageManager)

    val heatmapEngine = HeatmapEngine()
    val superChatEngine = SuperChatEngine()
    val chatVelocityEngine = ChatVelocityEngine()
    val transcriptExcitementEngine = TranscriptExcitementEngine()
    val consensusMerger = ConsensusMerger()
}
'''

FILES["app/src/main/java/com/clipperzero/app/ClipperZeroApp.kt"] = r'''
package com.clipperzero.app

import android.app.Application

class ClipperZeroApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(applicationContext)
    }
}
'''

# ---------- VIEWMODELS ----------

FILES["app/src/main/java/com/clipperzero/app/viewmodel/AiSettingsViewModel.kt"] = r'''
package com.clipperzero.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clipperzero.app.AppContainer
import com.clipperzero.app.domain.model.AiConfig
import com.clipperzero.app.domain.model.AiProviderPreset
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.util.UrlNormalizer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AiSettingsUiState(
    val config: AiConfig = AiConfig(),
    val availableModels: List<String> = AiProviderPreset.DEEPSEEK.defaultModels,
    val modelSearchQuery: String = "",
    val isTesting: Boolean = false,
    val isLoadingModels: Boolean = false
)

class AiSettingsViewModel(private val container: AppContainer) : ViewModel() {

    private val _uiState = MutableStateFlow(
        AiSettingsUiState(
            config = container.prefs.loadAiConfig(),
            availableModels = container.prefs.loadAiConfig().preset.defaultModels
        )
    )
    val uiState: StateFlow<AiSettingsUiState> = _uiState.asStateFlow()

    fun selectPreset(preset: AiProviderPreset) {
        val updated = _uiState.value.config.copy(
            preset = preset,
            baseUrl = preset.defaultBaseUrl,
            model = preset.defaultModels.first(),
            isConnected = false,
            lastStatusMessage = "Preset changed"
        )
        container.prefs.saveAiConfig(updated)
        _uiState.update {
            it.copy(config = updated, availableModels = preset.defaultModels, modelSearchQuery = "")
        }
    }

    fun updateBaseUrl(url: String) {
        val updated = _uiState.value.config.copy(baseUrl = url)
        container.prefs.saveAiConfig(updated)
        _uiState.update { it.copy(config = updated) }
    }

    fun updatePrimaryKey(key: String) {
        val updated = _uiState.value.config.copy(primaryKey = key)
        container.prefs.saveAiConfig(updated)
        _uiState.update { it.copy(config = updated) }
    }

    fun updateBackupKey(key: String) {
        val updated = _uiState.value.config.copy(backupKey = key)
        container.prefs.saveAiConfig(updated)
        _uiState.update { it.copy(config = updated) }
    }

    fun updateModel(model: String) {
        val updated = _uiState.value.config.copy(model = model)
        container.prefs.saveAiConfig(updated)
        _uiState.update { it.copy(config = updated) }
    }

    fun updateModelSearch(query: String) {
        _uiState.update { it.copy(modelSearchQuery = query) }
    }

    fun setOfflineMode(offline: Boolean) {
        val updated = _uiState.value.config.copy(
            offlineMode = offline,
            lastStatusMessage = if (offline) "Offline No-AI mode" else "Ready to connect"
        )
        container.prefs.saveAiConfig(updated)
        _uiState.update { it.copy(config = updated) }
    }

    fun refreshModels() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingModels = true) }
            val cfg = _uiState.value.config.copy(
                baseUrl = UrlNormalizer.normalizeAiBaseUrl(_uiState.value.config.baseUrl)
            )
            when (val res = container.aiClient.fetchModels(cfg)) {
                is AppResult.Success -> {
                    _uiState.update { it.copy(availableModels = res.data, isLoadingModels = false) }
                }
                is AppResult.Error -> {
                    _uiState.update { it.copy(isLoadingModels = false) }
                }
            }
        }
    }

    fun connectAndProbe() {
        viewModelScope.launch {
            val normalizedUrl = UrlNormalizer.normalizeAiBaseUrl(_uiState.value.config.baseUrl)
            val current = _uiState.value.config.copy(baseUrl = normalizedUrl)
            _uiState.update { it.copy(config = current, isTesting = true) }

            when (val res = container.aiClient.testConnection(current)) {
                is AppResult.Success -> {
                    val saved = current.copy(
                        isConnected = !current.offlineMode,
                        lastStatusMessage = res.data
                    )
                    container.prefs.saveAiConfig(saved)
                    _uiState.update { it.copy(config = saved, isTesting = false) }
                }
                is AppResult.Error -> {
                    val saved = current.copy(
                        isConnected = false,
                        lastStatusMessage = res.message
                    )
                    container.prefs.saveAiConfig(saved)
                    _uiState.update { it.copy(config = saved, isTesting = false) }
                }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/viewmodel/DownloadsViewModel.kt"] = r'''
package com.clipperzero.app.viewmodel

import android.net.Uri
import androidx.lifecycle.ViewModel
import com.clipperzero.app.AppContainer
import com.clipperzero.app.domain.model.ExportJob
import com.clipperzero.app.domain.model.StorageConfig
import com.clipperzero.app.domain.model.StoragePreset
import com.clipperzero.app.service.ExportForegroundService
import com.clipperzero.app.service.ExportQueueState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class DownloadsUiState(
    val storageConfig: StorageConfig = StorageConfig()
)

class DownloadsViewModel(private val container: AppContainer) : ViewModel() {

    val jobs: StateFlow<List<ExportJob>> = ExportQueueState.jobs

    private val _uiState = MutableStateFlow(
        DownloadsUiState(storageConfig = container.prefs.loadStorageConfig())
    )
    val uiState: StateFlow<DownloadsUiState> = _uiState.asStateFlow()

    fun selectStoragePreset(preset: StoragePreset) {
        val updated = _uiState.value.storageConfig.copy(preset = preset)
        container.prefs.saveStorageConfig(updated)
        _uiState.update { it.copy(storageConfig = updated) }
    }

    fun setSafFolder(uri: Uri, displayName: String) {
        val updated = StorageConfig(
            preset = StoragePreset.CUSTOM_SAF,
            safTreeUri = uri.toString(),
            safDisplayName = displayName
        )
        container.prefs.saveStorageConfig(updated)
        _uiState.update { it.copy(storageConfig = updated) }
    }

    fun cancelJob(jobId: String) {
        ExportForegroundService.cancel(container.appContext, jobId)
    }

    fun clearCompleted() {
        ExportQueueState.clearCompleted()
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/viewmodel/StudioViewModel.kt"] = r'''
package com.clipperzero.app.viewmodel

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clipperzero.app.AppContainer
import com.clipperzero.app.domain.engine.ViralCopyGenerator
import com.clipperzero.app.domain.model.AppResult
import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.ExportJob
import com.clipperzero.app.domain.model.ExportOptions
import com.clipperzero.app.domain.model.PaddingPreset
import com.clipperzero.app.domain.model.ScanHistoryItem
import com.clipperzero.app.domain.model.Signal
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.domain.model.VideoMetadata
import com.clipperzero.app.service.ExportForegroundService
import com.clipperzero.app.service.ExportQueueState
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class ClipFilter(val label: String) {
    ALL("All"),
    MULTI("Multi-Signal"),
    HEATMAP("Heatmap"),
    SUPER_CHAT("Super Chat"),
    CHAT_HYPE("Chat Hype"),
    AI_PICK("AI Pick")
}

data class StudioUiState(
    val inputUrl: String = "",
    val isScanning: Boolean = false,
    val scanStage: String = "",
    val errorMessage: String? = null,
    val statusBanner: String? = null,
    val video: VideoMetadata? = null,
    val rawSignals: List<Signal> = emptyList(),
    val clips: List<ClipCandidate> = emptyList(),
    val selectedClipId: String? = null,
    val expandedClipId: String? = null,
    val activeFilter: ClipFilter = ClipFilter.ALL,
    val paddingPreset: PaddingPreset = PaddingPreset.BALANCED,
    val exportOptions: ExportOptions = ExportOptions(),
    val hasCookies: Boolean = false,
    val isUpdatingYtDlp: Boolean = false,
    val scanHistory: List<ScanHistoryItem> = emptyList(),
    val fetchLiveChatEnabled: Boolean = false
) {
    val filteredClips: List<ClipCandidate>
        get() = when (activeFilter) {
            ClipFilter.ALL -> clips
            ClipFilter.MULTI -> clips.filter { it.isMultiSignal }.ifEmpty { clips }
            ClipFilter.HEATMAP -> clips.filter { SignalType.HEATMAP in it.signalTypes }
            ClipFilter.SUPER_CHAT -> clips.filter { SignalType.SUPER_CHAT in it.signalTypes }
            ClipFilter.CHAT_HYPE -> clips.filter { SignalType.CHAT_HYPE in it.signalTypes }
            ClipFilter.AI_PICK -> clips.filter { SignalType.AI_PICK in it.signalTypes }
        }

    val selectedClip: ClipCandidate?
        get() = clips.firstOrNull { it.id == selectedClipId } ?: filteredClips.firstOrNull()
}

class StudioViewModel(private val container: AppContainer) : ViewModel() {

    private val _uiState = MutableStateFlow(
        StudioUiState(
            hasCookies = container.ytDlpRepository.hasCookies(),
            scanHistory = container.prefs.loadScanHistory()
        )
    )
    val uiState: StateFlow<StudioUiState> = _uiState.asStateFlow()

    private var scanJob: Job? = null

    init {
        viewModelScope.launch {
            val msg = container.ytDlpRepository.autoUpdateIfDue()
            if (msg != null) {
                _uiState.update { it.copy(statusBanner = msg) }
            }
        }
    }

    fun updateInputUrl(url: String) {
        _uiState.update { it.copy(inputUrl = url, errorMessage = null) }
    }

    fun toggleFetchLiveChat(enabled: Boolean) {
        _uiState.update { it.copy(fetchLiveChatEnabled = enabled) }
    }

    fun dismissBanner() {
        _uiState.update { it.copy(statusBanner = null, errorMessage = null) }
    }

    fun importCookies(uri: Uri) {
        viewModelScope.launch {
            when (val res = container.ytDlpRepository.importCookies(uri)) {
                is AppResult.Success -> _uiState.update {
                    it.copy(hasCookies = true, statusBanner = res.data)
                }
                is AppResult.Error -> _uiState.update {
                    it.copy(errorMessage = res.message)
                }
            }
        }
    }

    fun clearCookies() {
        container.ytDlpRepository.clearCookies()
        _uiState.update { it.copy(hasCookies = false, statusBanner = "Cookies cleared") }
    }

    fun manualUpdateYtDlp() {
        if (_uiState.value.isUpdatingYtDlp) return
        viewModelScope.launch {
            _uiState.update { it.copy(isUpdatingYtDlp = true, statusBanner = "Updating yt-dlp...") }
            when (val res = container.ytDlpRepository.updateYtDlp()) {
                is AppResult.Success -> _uiState.update {
                    it.copy(isUpdatingYtDlp = false, statusBanner = res.data)
                }
                is AppResult.Error -> _uiState.update {
                    it.copy(isUpdatingYtDlp = false, errorMessage = res.message)
                }
            }
        }
    }

    fun handleIncomingShareOrLocal(uriOrText: String) {
        _uiState.update { it.copy(inputUrl = uriOrText, errorMessage = null) }
        scanCurrentInput()
    }

    fun cancelScan() {
        scanJob?.cancel()
        _uiState.update { it.copy(isScanning = false, scanStage = "") }
    }

    fun scanCurrentInput() {
        val input = _uiState.value.inputUrl.trim()
        if (input.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Paste a YouTube, Facebook, or local video first") }
            return
        }

        scanJob?.cancel()
        scanJob = viewModelScope.launch {
            _uiState.update {
                it.copy(
                    isScanning = true,
                    scanStage = "Starting metadata scan...",
                    errorMessage = null,
                    statusBanner = null
                )
            }

            val metaResult = container.ytDlpRepository.scanSource(
                rawInput = input,
                fetchLiveChat = _uiState.value.fetchLiveChatEnabled
            ) { stage ->
                _uiState.update { it.copy(scanStage = stage) }
            }

            when (metaResult) {
                is AppResult.Error -> {
                    _uiState.update {
                        it.copy(isScanning = false, scanStage = "", errorMessage = metaResult.message)
                    }
                }
                is AppResult.Success -> {
                    val video = metaResult.data
                    _uiState.update { it.copy(scanStage = "Running signal engines...") }

                    val allSignals = mutableListOf<Signal>()
                    allSignals.addAll(container.heatmapEngine.detect(video.heatmap, video.durationSec))
                    allSignals.addAll(container.superChatEngine.detectFromLiveChatFile(video.liveChatFilePath, video.durationSec))
                    allSignals.addAll(container.chatVelocityEngine.detectFromLiveChatFile(video.liveChatFilePath, video.durationSec))
                    allSignals.addAll(container.transcriptExcitementEngine.detect(video.transcript, video.durationSec))

                    val aiCfg = container.prefs.loadAiConfig()
                    if (!aiCfg.offlineMode && aiCfg.isConnected && video.transcript.isNotEmpty()) {
                        _uiState.update { it.copy(scanStage = "Asking AI for viral picks...") }
                        val aiRes = container.aiClient.detectAiPicks(aiCfg, video)
                        if (aiRes is AppResult.Success) {
                            allSignals.addAll(aiRes.data)
                        }
                    }

                    val merged = container.consensusMerger.merge(
                        signals = allSignals,
                        durationSec = video.durationSec,
                        padding = _uiState.value.paddingPreset
                    ).map { clip ->
                        clip.copy(viralCopy = ViralCopyGenerator.generateOffline(video, clip))
                    }

                    val history = container.prefs.addScanHistory(
                        ScanHistoryItem(
                            url = video.normalizedUrl,
                            title = video.title,
                            uploader = video.uploader,
                            durationSec = video.durationSec,
                            clipCount = merged.size,
                            scannedAtMs = System.currentTimeMillis()
                        )
                    )

                    _uiState.update {
                        it.copy(
                            isScanning = false,
                            scanStage = "",
                            video = video,
                            rawSignals = allSignals,
                            clips = merged,
                            selectedClipId = merged.firstOrNull()?.id,
                            expandedClipId = merged.firstOrNull()?.id,
                            scanHistory = history,
                            statusBanner = "Found ${merged.size} clips"
                        )
                    }
                }
            }
        }
    }

    fun setFilter(filter: ClipFilter) {
        _uiState.update { it.copy(activeFilter = filter) }
    }

    fun setPaddingPreset(preset: PaddingPreset) {
        val video = _uiState.value.video
        if (video == null) {
            _uiState.update { it.copy(paddingPreset = preset) }
            return
        }
        val remerged = container.consensusMerger.merge(
            signals = _uiState.value.rawSignals,
            durationSec = video.durationSec,
            padding = preset
        ).map { clip ->
            clip.copy(viralCopy = ViralCopyGenerator.generateOffline(video, clip))
        }
        _uiState.update {
            it.copy(
                paddingPreset = preset,
                clips = remerged,
                selectedClipId = remerged.firstOrNull()?.id,
                expandedClipId = remerged.firstOrNull()?.id
            )
        }
    }

    fun selectAndToggleExpand(clipId: String) {
        _uiState.update {
            val nextExpand = if (it.expandedClipId == clipId) null else clipId
            it.copy(selectedClipId = clipId, expandedClipId = nextExpand)
        }
    }

    fun updateClipBounds(clipId: String, newStart: Double, newEnd: Double) {
        val maxDur = _uiState.value.video?.durationSec?.coerceAtLeast(1.0) ?: 3600.0
        val clampedStart = newStart.coerceIn(0.0, (maxDur - 1.0).coerceAtLeast(0.0))
        val clampedEnd = newEnd.coerceIn((clampedStart + 1.0).coerceAtMost(maxDur), maxDur)
        _uiState.update { state ->
            state.copy(
                clips = state.clips.map { clip ->
                    if (clip.id == clipId) clip.copy(startSec = clampedStart, endSec = clampedEnd)
                    else clip
                }
            )
        }
    }

    fun nudgeClip(clipId: String, deltaStart: Double, deltaEnd: Double) {
        val clip = _uiState.value.clips.firstOrNull { it.id == clipId } ?: return
        updateClipBounds(clipId, clip.startSec + deltaStart, clip.endSec + deltaEnd)
    }

    fun addCustomClip(startSec: Double, endSec: Double, label: String) {
        val video = _uiState.value.video ?: return
        val maxDur = video.durationSec.coerceAtLeast(1.0)
        val s = startSec.coerceIn(0.0, (maxDur - 1.0).coerceAtLeast(0.0))
        val e = endSec.coerceIn((s + 1.0).coerceAtMost(maxDur), maxDur)
        val custom = ClipCandidate(
            startSec = s,
            endSec = e,
            score = 1.0,
            primaryType = SignalType.CUSTOM,
            signalTypes = setOf(SignalType.CUSTOM),
            reason = label.ifBlank { "Custom clip" }
        ).let { it.copy(viralCopy = ViralCopyGenerator.generateOffline(video, it)) }

        _uiState.update {
            it.copy(
                clips = listOf(custom) + it.clips,
                selectedClipId = custom.id,
                expandedClipId = custom.id,
                activeFilter = ClipFilter.ALL
            )
        }
    }

    fun enhanceViralCopyWithAi(clipId: String) {
        val video = _uiState.value.video ?: return
        val clip = _uiState.value.clips.firstOrNull { it.id == clipId } ?: return
        val aiCfg = container.prefs.loadAiConfig()
        viewModelScope.launch {
            when (val res = container.aiClient.generateViralCopy(aiCfg, video, clip)) {
                is AppResult.Success -> {
                    _uiState.update { state ->
                        state.copy(
                            clips = state.clips.map {
                                if (it.id == clipId) it.copy(viralCopy = res.data) else it
                            },
                            statusBanner = "AI viral pack generated"
                        )
                    }
                }
                is AppResult.Error -> {
                    val offline = ViralCopyGenerator.generateOffline(video, clip)
                    _uiState.update { state ->
                        state.copy(
                            clips = state.clips.map {
                                if (it.id == clipId) it.copy(viralCopy = offline) else it
                            },
                            statusBanner = "Used offline viral pack (${res.message})"
                        )
                    }
                }
            }
        }
    }

    fun updateExportOptions(transform: (ExportOptions) -> ExportOptions) {
        _uiState.update { it.copy(exportOptions = transform(it.exportOptions)) }
    }

    fun enqueueSelectedExport() {
        val video = _uiState.value.video ?: return
        val clip = _uiState.value.selectedClip ?: return
        val job = ExportJob(
            clipId = clip.id,
            title = clip.viralCopy?.title ?: video.title,
            sourceUrl = video.normalizedUrl,
            localUri = video.localUri,
            startSec = clip.startSec,
            endSec = clip.endSec,
            options = _uiState.value.exportOptions,
            superChat = clip.superChat,
            viralCopy = clip.viralCopy
        )
        ExportQueueState.enqueue(job)
        ExportForegroundService.start(container.appContext)
        _uiState.update { it.copy(statusBanner = "Queued export: ${clip.viralCopy?.title?.take(36) ?: video.title.take(36)}") }
    }
}
'''

# ---------- THEME ----------

FILES["app/src/main/java/com/clipperzero/app/ui/theme/Color.kt"] = r'''
package com.clipperzero.app.ui.theme

import androidx.compose.ui.graphics.Color

val ObsidianBg = Color(0xFF0B0B0F)
val SlateSurface = Color(0xFF16161D)
val ElevatedSurface = Color(0xFF1F1F29)
val HairlineBorder = Color(0xFF262633)
val IndigoAccent = Color(0xFF6366F1)

val TextPrimary = Color(0xFFF3F4F6)
val TextSecondary = Color(0xFF9CA3AF)

val SignalCrimson = Color(0xFFEF4444)
val SignalGold = Color(0xFFF59E0B)
val SignalPurple = Color(0xFFA855F7)
val SignalCyan = Color(0xFF06B6D4)
val SignalEmerald = Color(0xFF10B981)
'''

FILES["app/src/main/java/com/clipperzero/app/ui/theme/Type.kt"] = r'''
package com.clipperzero.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val MonoTimestampStyle = TextStyle(
    fontFamily = FontFamily.Monospace,
    fontWeight = FontWeight.SemiBold,
    fontSize = 12.sp,
    color = TextPrimary
)

val ClipperTypography = Typography(
    titleLarge = TextStyle(
        fontWeight = FontWeight.Bold,
        fontSize = 20.sp,
        color = TextPrimary
    ),
    titleMedium = TextStyle(
        fontWeight = FontWeight.SemiBold,
        fontSize = 15.sp,
        color = TextPrimary
    ),
    bodyMedium = TextStyle(
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        color = TextPrimary
    ),
    bodySmall = TextStyle(
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        color = TextSecondary
    ),
    labelMedium = TextStyle(
        fontWeight = FontWeight.Medium,
        fontSize = 12.sp,
        color = TextPrimary
    )
)
'''

FILES["app/src/main/java/com/clipperzero/app/ui/theme/Theme.kt"] = r'''
package com.clipperzero.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkScheme = darkColorScheme(
    primary = IndigoAccent,
    onPrimary = TextPrimary,
    background = ObsidianBg,
    onBackground = TextPrimary,
    surface = SlateSurface,
    onSurface = TextPrimary,
    surfaceVariant = ElevatedSurface,
    onSurfaceVariant = TextSecondary,
    outline = HairlineBorder,
    error = SignalCrimson
)

@Composable
fun ClipperZeroTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkScheme,
        typography = ClipperTypography,
        content = content
    )
}
'''

# ---------- UI COMPONENTS ----------

FILES["app/src/main/java/com/clipperzero/app/ui/components/HeatmapChart.kt"] = r'''
package com.clipperzero.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.HeatmapPoint
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.MonoTimestampStyle
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.util.TimeFormatters

@Composable
fun HeatmapChart(
    points: List<HeatmapPoint>,
    durationSec: Double,
    selectedClip: ClipCandidate?,
    onTapTimestamp: (Double) -> Unit,
    modifier: Modifier = Modifier
) {
    if (durationSec <= 0.0) return

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = SlateSurface,
        border = BorderStroke(1.dp, HairlineBorder)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = if (points.isNotEmpty()) "INTERACTIVE HEATMAP" else "TIMELINE OVERVIEW",
                    style = MonoTimestampStyle,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    text = TimeFormatters.formatTimestamp(durationSec),
                    style = MonoTimestampStyle,
                    color = TextSecondary
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(68.dp)
                    .pointerInput(durationSec) {
                        detectTapGestures { offset ->
                            val frac = (offset.x / size.width.toFloat()).coerceIn(0f, 1f)
                            onTapTimestamp(frac.toDouble() * durationSec)
                        }
                    }
            ) {
                val w = size.width
                val h = size.height

                if (selectedClip != null) {
                    val x1 = ((selectedClip.startSec / durationSec).toFloat().coerceIn(0f, 1f)) * w
                    val x2 = ((selectedClip.endSec / durationSec).toFloat().coerceIn(0f, 1f)) * w
                    drawRect(
                        color = IndigoAccent.copy(alpha = 0.25f),
                        topLeft = Offset(x1, 0f),
                        size = Size((x2 - x1).coerceAtLeast(4f), h)
                    )
                }

                if (points.size >= 2) {
                    val maxV = points.maxOf { it.value }.coerceAtLeast(0.01)
                    val linePath = Path()
                    val fillPath = Path()
                    points.forEachIndexed { idx, pt ->
                        val x = ((pt.startTime / durationSec).toFloat().coerceIn(0f, 1f)) * w
                        val y = h - ((pt.value / maxV).toFloat().coerceIn(0f, 1f)) * (h - 6f)
                        if (idx == 0) {
                            linePath.moveTo(x, y)
                            fillPath.moveTo(x, h)
                            fillPath.lineTo(x, y)
                        } else {
                            linePath.lineTo(x, y)
                            fillPath.lineTo(x, y)
                        }
                    }
                    fillPath.lineTo(w, h)
                    fillPath.close()

                    drawPath(
                        path = fillPath,
                        brush = Brush.verticalGradient(
                            colors = listOf(SignalCrimson.copy(alpha = 0.45f), SignalCrimson.copy(alpha = 0.02f))
                        )
                    )
                    drawPath(
                        path = linePath,
                        color = SignalCrimson,
                        style = Stroke(width = 3f)
                    )
                } else {
                    drawLine(
                        color = HairlineBorder,
                        start = Offset(0f, h / 2f),
                        end = Offset(w, h / 2f),
                        strokeWidth = 4f
                    )
                }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/components/Media3PreviewPlayer.kt"] = r'''
package com.clipperzero.app.ui.components

import android.net.Uri
import androidx.annotation.OptIn
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.ui.PlayerView
import com.clipperzero.app.ui.theme.ObsidianBg
import com.clipperzero.app.ui.theme.TextSecondary

@OptIn(UnstableApi::class)
@Composable
fun Media3PreviewPlayer(
    streamUrl: String?,
    startSec: Double,
    endSec: Double,
    modifier: Modifier = Modifier
) {
    if (streamUrl.isNullOrBlank()) {
        Box(
            modifier = modifier
                .fillMaxWidth()
                .height(180.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(ObsidianBg),
            contentAlignment = Alignment.Center
        ) {
            Text("Preview stream unavailable for this source", color = TextSecondary)
        }
        return
    }

    val context = LocalContext.current
    val player = remember(streamUrl) {
        val httpFactory = DefaultHttpDataSource.Factory()
            .setUserAgent("Mozilla/5.0 (Android 14; Mobile) ClipperZero/1.0")
            .setAllowCrossProtocolRedirects(true)
        val dataSourceFactory = DefaultDataSource.Factory(context, httpFactory)
        val mediaSourceFactory = DefaultMediaSourceFactory(context)
            .setDataSourceFactory(dataSourceFactory)

        ExoPlayer.Builder(context)
            .setMediaSourceFactory(mediaSourceFactory)
            .build()
    }

    LaunchedEffect(streamUrl, startSec, endSec) {
        val startMs = (startSec * 1000.0).toLong().coerceAtLeast(0L)
        val endMs = (endSec * 1000.0).toLong().coerceAtLeast(startMs + 1000L)
        val mediaItem = MediaItem.Builder()
            .setUri(Uri.parse(streamUrl))
            .setClippingConfiguration(
                MediaItem.ClippingConfiguration.Builder()
                    .setStartPositionMs(startMs)
                    .setEndPositionMs(endMs)
                    .build()
            )
            .build()
        player.setMediaItem(mediaItem)
        player.prepare()
        player.playWhenReady = false
    }

    DisposableEffect(player) {
        onDispose {
            player.release()
        }
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(200.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Color.Black)
    ) {
        AndroidView(
            factory = { ctx ->
                PlayerView(ctx).apply {
                    this.player = player
                    useController = true
                }
            },
            modifier = Modifier.fillMaxSize()
        )
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/components/ClipCard.kt"] = r'''
package com.clipperzero.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RangeSlider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.clipperzero.app.domain.model.ClipCandidate
import com.clipperzero.app.domain.model.SignalType
import com.clipperzero.app.ui.theme.ElevatedSurface
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.MonoTimestampStyle
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SignalCyan
import com.clipperzero.app.ui.theme.SignalEmerald
import com.clipperzero.app.ui.theme.SignalGold
import com.clipperzero.app.ui.theme.SignalPurple
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.util.TimeFormatters

fun signalColor(type: SignalType): Color = when (type) {
    SignalType.HEATMAP -> SignalCrimson
    SignalType.SUPER_CHAT -> SignalGold
    SignalType.CHAT_HYPE -> SignalPurple
    SignalType.AI_PICK -> SignalCyan
    SignalType.TRANSCRIPT -> SignalEmerald
    SignalType.CUSTOM -> IndigoAccent
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ClipCard(
    clip: ClipCandidate,
    durationSec: Double,
    previewUrl: String?,
    isSelected: Boolean,
    isExpanded: Boolean,
    onSelectToggle: () -> Unit,
    onBoundsChange: (Double, Double) -> Unit,
    onNudge: (Double, Double) -> Unit,
    onEnhanceCopy: () -> Unit,
    onCopiedNotice: (String) -> Unit
) {
    val clipboard = LocalClipboardManager.current
    val borderColor = if (isSelected) IndigoAccent else HairlineBorder

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelectToggle() },
        shape = RoundedCornerShape(16.dp),
        color = SlateSurface,
        border = BorderStroke(if (isSelected) 1.5.dp else 1.dp, borderColor)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${TimeFormatters.formatTimestamp(clip.startSec)} - ${TimeFormatters.formatTimestamp(clip.endSec)}",
                    style = MonoTimestampStyle
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "(${clip.durationSec.toInt()}s)",
                    style = MonoTimestampStyle,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    text = "${(clip.score * 100.0).toInt()}%",
                    style = MonoTimestampStyle,
                    color = signalColor(clip.primaryType)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Icon(
                    imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = "Toggle clip details",
                    tint = TextSecondary
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                if (clip.isMultiSignal) {
                    BadgePill(label = "Multi-Signal", color = IndigoAccent)
                }
                clip.signalTypes.forEach { t ->
                    BadgePill(label = t.label, color = signalColor(t))
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = clip.viralCopy?.title ?: clip.reason,
                color = TextPrimary,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp
            )

            if (clip.superChat != null) {
                Spacer(modifier = Modifier.height(6.dp))
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = SignalGold.copy(alpha = 0.14f),
                    border = BorderStroke(1.dp, SignalGold.copy(alpha = 0.5f))
                ) {
                    Text(
                        text = "${clip.superChat.amountDisplay} • ${clip.superChat.author}: ${clip.superChat.message}",
                        color = SignalGold,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                    )
                }
            }

            if (isExpanded) {
                Spacer(modifier = Modifier.height(12.dp))
                Media3PreviewPlayer(
                    streamUrl = previewUrl,
                    startSec = clip.startSec,
                    endSec = clip.endSec
                )

                Spacer(modifier = Modifier.height(10.dp))

                val maxRange = durationSec.toFloat().coerceAtLeast(2f)
                val safeStart = clip.startSec.toFloat().coerceIn(0f, maxRange - 1f)
                val safeEnd = clip.endSec.toFloat().coerceIn(safeStart + 1f, maxRange)

                Text("DRAG TO TRIM", style = MonoTimestampStyle, color = TextSecondary)
                RangeSlider(
                    value = safeStart..safeEnd,
                    onValueChange = { range ->
                        onBoundsChange(range.start.toDouble(), range.endInclusive.toDouble())
                    },
                    valueRange = 0f..maxRange,
                    colors = SliderDefaults.colors(
                        thumbColor = IndigoAccent,
                        activeTrackColor = IndigoAccent,
                        inactiveTrackColor = HairlineBorder
                    )
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    NudgeButton("-2s In", Modifier.weight(1f)) { onNudge(-2.0, 0.0) }
                    NudgeButton("+2s In", Modifier.weight(1f)) { onNudge(2.0, 0.0) }
                    NudgeButton("-2s Out", Modifier.weight(1f)) { onNudge(0.0, -2.0) }
                    NudgeButton("+2s Out", Modifier.weight(1f)) { onNudge(0.0, 2.0) }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            val text = clip.viralCopy?.formattedPack() ?: clip.reason
                            clipboard.setText(AnnotatedString(text))
                            onCopiedNotice("Viral pack copied")
                        },
                        modifier = Modifier
                            .weight(1f)
                            .heightIn(min = 48.dp),
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, HairlineBorder)
                    ) {
                        Icon(Icons.Default.ContentCopy, contentDescription = null, tint = TextPrimary)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Copy Pack", color = TextPrimary, fontSize = 12.sp)
                    }

                    OutlinedButton(
                        onClick = onEnhanceCopy,
                        modifier = Modifier
                            .weight(1f)
                            .heightIn(min = 48.dp),
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, SignalCyan.copy(alpha = 0.6f))
                    ) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = SignalCyan)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("AI Titles", color = SignalCyan, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun BadgePill(label: String, color: Color) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = color.copy(alpha = 0.16f),
        border = BorderStroke(1.dp, color.copy(alpha = 0.5f))
    ) {
        Text(
            text = label,
            color = color,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        )
    }
}

@Composable
private fun NudgeButton(
    label: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Surface(
        modifier = modifier
            .heightIn(min = 48.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        color = ElevatedSurface,
        border = BorderStroke(1.dp, HairlineBorder)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
            modifier = Modifier.padding(horizontal = 4.dp)
        ) {
            Text(text = label, style = MonoTimestampStyle, fontSize = 11.sp)
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/components/ExportDock.kt"] = r'''
package com.clipperzero.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.clipperzero.app.domain.model.ExportOptions
import com.clipperzero.app.ui.theme.ElevatedSurface
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.MonoTimestampStyle
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary

@Composable
fun ExportDock(
    options: ExportOptions,
    hasSuperChat: Boolean,
    canExport: Boolean,
    onUpdateOptions: ((ExportOptions) -> ExportOptions) -> Unit,
    onExportClick: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = SlateSurface,
        border = BorderStroke(1.dp, HairlineBorder)
    ) {
        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                DockToggle("Fast Cut", options.fastCut) {
                    onUpdateOptions { o -> o.copy(fastCut = !o.fastCut) }
                }
                DockToggle("9:16 Crop", options.cropVertical916) {
                    onUpdateOptions { o ->
                        val next = !o.cropVertical916
                        o.copy(cropVertical916 = next, fastCut = if (next) false else o.fastCut)
                    }
                }
                DockToggle("SC Overlay", options.superChatOverlay && hasSuperChat, enabled = hasSuperChat) {
                    onUpdateOptions { o ->
                        val next = !o.superChatOverlay
                        o.copy(superChatOverlay = next, fastCut = if (next) false else o.fastCut)
                    }
                }
                DockToggle("Audio Level", options.audioLoudnorm) {
                    onUpdateOptions { o ->
                        val next = !o.audioLoudnorm
                        o.copy(audioLoudnorm = next, fastCut = if (next) false else o.fastCut)
                    }
                }
                DockToggle("TXT", options.writeSidecarTxt) {
                    onUpdateOptions { o -> o.copy(writeSidecarTxt = !o.writeSidecarTxt) }
                }
            }

            if (options.cropVertical916) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "CROP X ${(options.cropOffsetX * 100f).toInt()}%",
                        style = MonoTimestampStyle,
                        color = TextSecondary
                    )
                    Slider(
                        value = options.cropOffsetX.coerceIn(0f, 1f),
                        onValueChange = { v -> onUpdateOptions { o -> o.copy(cropOffsetX = v) } },
                        valueRange = 0f..1f,
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = 10.dp),
                        colors = SliderDefaults.colors(
                            thumbColor = IndigoAccent,
                            activeTrackColor = IndigoAccent
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Button(
                onClick = onExportClick,
                enabled = canExport,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = IndigoAccent)
            ) {
                Text("Export Selected Clip", color = TextPrimary, fontSize = 14.sp)
            }
        }
    }
}

@Composable
private fun DockToggle(
    label: String,
    selected: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit
) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        enabled = enabled,
        label = { Text(label, fontSize = 12.sp) },
        shape = RoundedCornerShape(12.dp),
        colors = FilterChipDefaults.filterChipColors(
            containerColor = ElevatedSurface,
            selectedContainerColor = IndigoAccent.copy(alpha = 0.25f),
            labelColor = TextSecondary,
            selectedLabelColor = TextPrimary
        ),
        border = FilterChipDefaults.filterChipBorder(
            enabled = enabled,
            selected = selected,
            borderColor = HairlineBorder,
            selectedBorderColor = IndigoAccent
        )
    )
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/components/CustomClipDialog.kt"] = r'''
package com.clipperzero.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.util.TimeFormatters

@Composable
fun CustomClipDialog(
    initialStartSec: Double,
    durationSec: Double,
    onDismiss: () -> Unit,
    onConfirm: (Double, Double, String) -> Unit
) {
    var startText by remember { mutableStateOf(TimeFormatters.formatTimestamp(initialStartSec)) }
    var endText by remember {
        mutableStateOf(
            TimeFormatters.formatTimestamp((initialStartSec + 30.0).coerceAtMost(durationSec.coerceAtLeast(1.0)))
        )
    }
    var label by remember { mutableStateOf("Manual Highlight") }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = SlateSurface,
        title = { Text("Add Custom Clip", color = TextPrimary) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = startText,
                    onValueChange = { startText = it; error = null },
                    label = { Text("Start (MM:SS or HH:MM:SS)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = endText,
                    onValueChange = { endText = it; error = null },
                    label = { Text("End (MM:SS or HH:MM:SS)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = label,
                    onValueChange = { label = it },
                    label = { Text("Label") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                if (error != null) {
                    Text(error!!, color = com.clipperzero.app.ui.theme.SignalCrimson)
                } else {
                    Text("Max duration: ${TimeFormatters.formatTimestamp(durationSec)}", color = TextSecondary)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val s = TimeFormatters.parseTimeToSeconds(startText)
                val e = TimeFormatters.parseTimeToSeconds(endText)
                if (s == null || e == null || e <= s) {
                    error = "Enter valid start and end timestamps"
                } else {
                    onConfirm(s, e, label)
                }
            }) {
                Text("Add Clip")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/components/AiManagerSheet.kt"] = r'''
package com.clipperzero.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.clipperzero.app.domain.model.AiProviderPreset
import com.clipperzero.app.ui.theme.ElevatedSurface
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SignalEmerald
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.viewmodel.AiSettingsUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiManagerSheet(
    state: AiSettingsUiState,
    onDismiss: () -> Unit,
    onSelectPreset: (AiProviderPreset) -> Unit,
    onBaseUrlChange: (String) -> Unit,
    onPrimaryKeyChange: (String) -> Unit,
    onBackupKeyChange: (String) -> Unit,
    onModelChange: (String) -> Unit,
    onModelSearchChange: (String) -> Unit,
    onOfflineToggle: (Boolean) -> Unit,
    onRefreshModels: () -> Unit,
    onConnectProbe: () -> Unit
) {
    val cfg = state.config
    val filteredModels = state.availableModels.filter {
        state.modelSearchQuery.isBlank() || it.contains(state.modelSearchQuery, ignoreCase = true)
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = SlateSurface
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("AI Engine Manager", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                Spacer(modifier = Modifier.weight(1f))
                val badgeColor = when {
                    cfg.offlineMode -> TextSecondary
                    cfg.isConnected -> SignalEmerald
                    else -> SignalCrimson
                }
                Text(
                    text = if (cfg.offlineMode) "Offline" else if (cfg.isConnected) "Connected" else "Disconnected",
                    color = badgeColor,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Offline No-AI Mode", color = TextPrimary, modifier = Modifier.weight(1f))
                Switch(checked = cfg.offlineMode, onCheckedChange = onOfflineToggle)
            }

            if (!cfg.offlineMode) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    AiProviderPreset.entries.forEach { preset ->
                        FilterChip(
                            selected = cfg.preset == preset,
                            onClick = { onSelectPreset(preset) },
                            label = { Text(preset.displayName) },
                            shape = RoundedCornerShape(12.dp)
                        )
                    }
                }

                OutlinedTextField(
                    value = cfg.baseUrl,
                    onValueChange = onBaseUrlChange,
                    label = { Text("Base URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = cfg.primaryKey,
                    onValueChange = onPrimaryKeyChange,
                    label = { Text("Primary API Key") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = cfg.backupKey,
                    onValueChange = onBackupKeyChange,
                    label = { Text("Backup API Key (Failover on 401/402/403/429/5xx)") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = cfg.model,
                    onValueChange = onModelChange,
                    label = { Text("Selected Model") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = state.modelSearchQuery,
                        onValueChange = onModelSearchChange,
                        label = { Text("Search models") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedButton(
                        onClick = onRefreshModels,
                        enabled = !state.isLoadingModels,
                        modifier = Modifier.heightIn(min = 48.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(if (state.isLoadingModels) "..." else "Fetch")
                    }
                }

                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = ElevatedSurface,
                    border = BorderStroke(1.dp, HairlineBorder),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp)
                ) {
                    LazyColumn(modifier = Modifier.padding(6.dp)) {
                        items(filteredModels.take(60)) { m ->
                            Text(
                                text = m,
                                color = if (m == cfg.model) IndigoAccent else TextPrimary,
                                fontSize = 13.sp,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onModelChange(m) }
                                    .padding(horizontal = 8.dp, vertical = 8.dp)
                            )
                        }
                    }
                }
            }

            Text(
                text = cfg.lastStatusMessage,
                color = if (cfg.isConnected) SignalEmerald else TextSecondary,
                fontSize = 12.sp
            )

            Button(
                onClick = onConnectProbe,
                enabled = !state.isTesting,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = IndigoAccent)
            ) {
                if (state.isTesting) {
                    CircularProgressIndicator(
                        color = TextPrimary,
                        strokeWidth = 2.dp,
                        modifier = Modifier.height(20.dp)
                    )
                } else {
                    Text(if (cfg.offlineMode) "Save Offline Mode" else "Connect & Probe (max_tokens=16)")
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}
'''

# ---------- SCREENS & MAIN ACTIVITY ----------

FILES["app/src/main/java/com/clipperzero/app/ui/screens/ClipStudioScreen.kt"] = r'''
package com.clipperzero.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Cookie
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.clipperzero.app.domain.model.PaddingPreset
import com.clipperzero.app.ui.components.ClipCard
import com.clipperzero.app.ui.components.CustomClipDialog
import com.clipperzero.app.ui.components.ExportDock
import com.clipperzero.app.ui.components.HeatmapChart
import com.clipperzero.app.ui.theme.ElevatedSurface
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.MonoTimestampStyle
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SignalEmerald
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.util.TimeFormatters
import com.clipperzero.app.viewmodel.ClipFilter
import com.clipperzero.app.viewmodel.StudioUiState
import com.clipperzero.app.viewmodel.StudioViewModel

@Composable
fun ClipStudioScreen(
    state: StudioUiState,
    viewModel: StudioViewModel,
    onPickLocalVideo: () -> Unit,
    onPickCookiesFile: () -> Unit,
    onShowSnackbar: (String) -> Unit
) {
    var showCustomDialog by remember { mutableStateOf(false) }
    var customStartSeed by remember { mutableStateOf(0.0) }

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.weight(1f),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = SlateSurface,
                    border = BorderStroke(1.dp, HairlineBorder)
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = state.inputUrl,
                            onValueChange = viewModel::updateInputUrl,
                            label = { Text("YouTube, Livestream VOD, or Facebook URL") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                onClick = {
                                    if (state.isScanning) viewModel.cancelScan()
                                    else viewModel.scanCurrentInput()
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (state.isScanning) SignalCrimson else IndigoAccent
                                )
                            ) {
                                Icon(Icons.Default.Search, contentDescription = null)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(if (state.isScanning) "Cancel" else "Scan Video")
                            }

                            OutlinedButton(
                                onClick = onPickLocalVideo,
                                modifier = Modifier.heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                border = BorderStroke(1.dp, HairlineBorder)
                            ) {
                                Icon(Icons.Default.FolderOpen, contentDescription = "Local Video", tint = TextPrimary)
                            }
                        }

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedButton(
                                onClick = onPickCookiesFile,
                                modifier = Modifier.heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                border = BorderStroke(
                                    1.dp,
                                    if (state.hasCookies) SignalEmerald else HairlineBorder
                                )
                            ) {
                                Icon(
                                    Icons.Default.Cookie,
                                    contentDescription = null,
                                    tint = if (state.hasCookies) SignalEmerald else TextSecondary
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    if (state.hasCookies) "Cookies OK" else "cookies.txt",
                                    fontSize = 12.sp,
                                    color = TextPrimary
                                )
                            }

                            OutlinedButton(
                                onClick = viewModel::manualUpdateYtDlp,
                                enabled = !state.isUpdatingYtDlp,
                                modifier = Modifier.heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                border = BorderStroke(1.dp, HairlineBorder)
                            ) {
                                Icon(Icons.Default.Refresh, contentDescription = null, tint = TextSecondary)
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(if (state.isUpdatingYtDlp) "Updating" else "yt-dlp", fontSize = 12.sp, color = TextPrimary)
                            }

                            Spacer(modifier = Modifier.weight(1f))
                            Text("Chat", fontSize = 12.sp, color = TextSecondary)
                            Switch(
                                checked = state.fetchLiveChatEnabled,
                                onCheckedChange = viewModel::toggleFetchLiveChat
                            )
                        }

                        if (state.isScanning) {
                            LinearProgressIndicator(
                                modifier = Modifier.fillMaxWidth(),
                                color = IndigoAccent
                            )
                            Text(state.scanStage, fontSize = 12.sp, color = TextSecondary)
                        }

                        if (!state.errorMessage.isNullOrBlank()) {
                            Text(state.errorMessage, color = SignalCrimson, fontSize = 12.sp)
                        } else if (!state.statusBanner.isNullOrBlank()) {
                            Text(state.statusBanner, color = SignalEmerald, fontSize = 12.sp)
                        }
                    }
                }
            }

            if (state.video != null) {
                val video = state.video
                item {
                    Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = SlateSurface,
                        border = BorderStroke(1.dp, HairlineBorder)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(video.title, fontWeight = FontWeight.Bold, color = TextPrimary, fontSize = 15.sp)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "${video.uploader} • ${TimeFormatters.formatTimestamp(video.durationSec)}",
                                style = MonoTimestampStyle,
                                color = TextSecondary
                            )
                        }
                    }
                }

                item {
                    HeatmapChart(
                        points = video.heatmap,
                        durationSec = video.durationSec,
                        selectedClip = state.selectedClip,
                        onTapTimestamp = { tappedSec ->
                            customStartSeed = tappedSec
                            showCustomDialog = true
                        }
                    )
                }

                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        ClipFilter.entries.forEach { f ->
                            FilterChip(
                                selected = state.activeFilter == f,
                                onClick = { viewModel.setFilter(f) },
                                label = { Text(f.label, fontSize = 12.sp) },
                                shape = RoundedCornerShape(12.dp)
                            )
                        }
                    }
                }

                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            modifier = Modifier
                                .weight(1f)
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            PaddingPreset.entries.forEach { preset ->
                                FilterChip(
                                    selected = state.paddingPreset == preset,
                                    onClick = { viewModel.setPaddingPreset(preset) },
                                    label = { Text(preset.label, fontSize = 11.sp) },
                                    shape = RoundedCornerShape(12.dp)
                                )
                            }
                        }

                        OutlinedButton(
                            onClick = {
                                customStartSeed = state.selectedClip?.startSec ?: 0.0
                                showCustomDialog = true
                            },
                            modifier = Modifier.heightIn(min = 48.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, IndigoAccent)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, tint = IndigoAccent)
                            Text("Custom", color = IndigoAccent, fontSize = 12.sp)
                        }
                    }
                }

                items(state.filteredClips, key = { it.id }) { clip ->
                    ClipCard(
                        clip = clip,
                        durationSec = video.durationSec,
                        previewUrl = video.previewStreamUrl,
                        isSelected = state.selectedClip?.id == clip.id,
                        isExpanded = state.expandedClipId == clip.id,
                        onSelectToggle = { viewModel.selectAndToggleExpand(clip.id) },
                        onBoundsChange = { s, e -> viewModel.updateClipBounds(clip.id, s, e) },
                        onNudge = { ds, de -> viewModel.nudgeClip(clip.id, ds, de) },
                        onEnhanceCopy = { viewModel.enhanceViralCopyWithAi(clip.id) },
                        onCopiedNotice = onShowSnackbar
                    )
                }
            } else if (state.scanHistory.isNotEmpty()) {
                item {
                    Text(
                        "RECENT SCANS (${state.scanHistory.size})",
                        style = MonoTimestampStyle,
                        color = TextSecondary,
                        modifier = Modifier.padding(top = 6.dp)
                    )
                }
                items(state.scanHistory, key = { it.url + it.scannedAtMs }) { hist ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { viewModel.handleIncomingShareOrLocal(hist.url) },
                        shape = RoundedCornerShape(16.dp),
                        color = ElevatedSurface,
                        border = BorderStroke(1.dp, HairlineBorder)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(hist.title, color = TextPrimary, fontWeight = FontWeight.Medium, fontSize = 14.sp)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "${hist.uploader} • ${TimeFormatters.formatTimestamp(hist.durationSec)} • ${hist.clipCount} clips",
                                style = MonoTimestampStyle,
                                color = TextSecondary
                            )
                        }
                    }
                }
            }
        }

        if (state.video != null) {
            ExportDock(
                options = state.exportOptions,
                hasSuperChat = state.selectedClip?.superChat != null,
                canExport = state.selectedClip != null,
                onUpdateOptions = viewModel::updateExportOptions,
                onExportClick = {
                    viewModel.enqueueSelectedExport()
                    onShowSnackbar("Export started in background")
                }
            )
        }
    }

    if (showCustomDialog && state.video != null) {
        CustomClipDialog(
            initialStartSec = customStartSeed,
            durationSec = state.video.durationSec,
            onDismiss = { showCustomDialog = false },
            onConfirm = { s, e, label ->
                viewModel.addCustomClip(s, e, label)
                showCustomDialog = false
            }
        )
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/screens/DownloadsScreen.kt"] = r'''
package com.clipperzero.app.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.clipperzero.app.domain.model.ExportJob
import com.clipperzero.app.domain.model.ExportStatus
import com.clipperzero.app.domain.model.StoragePreset
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.IndigoAccent
import com.clipperzero.app.ui.theme.MonoTimestampStyle
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SignalEmerald
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.util.TimeFormatters
import com.clipperzero.app.viewmodel.DownloadsUiState

@Composable
fun DownloadsScreen(
    uiState: DownloadsUiState,
    jobs: List<ExportJob>,
    onSelectPreset: (StoragePreset) -> Unit,
    onPickSafFolder: () -> Unit,
    onCancelJob: (String) -> Unit,
    onClearCompleted: () -> Unit
) {
    val context = LocalContext.current

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = SlateSurface,
                border = BorderStroke(1.dp, HairlineBorder)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("OUTPUT STORAGE", style = MonoTimestampStyle, color = TextSecondary)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StoragePreset.entries.forEach { preset ->
                            FilterChip(
                                selected = uiState.storageConfig.preset == preset,
                                onClick = {
                                    if (preset == StoragePreset.CUSTOM_SAF) onPickSafFolder()
                                    else onSelectPreset(preset)
                                },
                                label = { Text(preset.label, fontSize = 12.sp) },
                                shape = RoundedCornerShape(12.dp)
                            )
                        }
                    }
                    if (uiState.storageConfig.preset == StoragePreset.CUSTOM_SAF &&
                        !uiState.storageConfig.safDisplayName.isNullOrBlank()
                    ) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "SAF Folder: ${uiState.storageConfig.safDisplayName}",
                            fontSize = 12.sp,
                            color = SignalEmerald
                        )
                    }
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("EXPORTS (${jobs.size})", style = MonoTimestampStyle, color = TextSecondary)
                Spacer(modifier = Modifier.weight(1f))
                if (jobs.any { it.status == ExportStatus.COMPLETED || it.status == ExportStatus.FAILED || it.status == ExportStatus.CANCELLED }) {
                    TextButton(onClick = onClearCompleted) {
                        Text("Clear Finished")
                    }
                }
            }
        }

        if (jobs.isEmpty()) {
            item {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = SlateSurface,
                    border = BorderStroke(1.dp, HairlineBorder),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "No exports yet. Select a clip in Clip Studio and tap Export.",
                        color = TextSecondary,
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }
        }

        items(jobs, key = { it.id }) { job ->
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = SlateSurface,
                border = BorderStroke(1.dp, HairlineBorder),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(job.title, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "${TimeFormatters.formatTimestamp(job.startSec)} - ${TimeFormatters.formatTimestamp(job.endSec)} • ${job.status.name}",
                        style = MonoTimestampStyle,
                        color = when (job.status) {
                            ExportStatus.COMPLETED -> SignalEmerald
                            ExportStatus.FAILED -> SignalCrimson
                            ExportStatus.RUNNING -> IndigoAccent
                            else -> TextSecondary
                        }
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(job.errorMessage ?: job.stage, fontSize = 12.sp, color = TextSecondary)

                    if (job.status == ExportStatus.RUNNING || job.status == ExportStatus.QUEUED) {
                        Spacer(modifier = Modifier.height(8.dp))
                        LinearProgressIndicator(
                            progress = { job.progress.coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth(),
                            color = IndigoAccent
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = { onCancelJob(job.id) },
                            modifier = Modifier.heightIn(min = 48.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, SignalCrimson)
                        ) {
                            Icon(Icons.Default.Cancel, contentDescription = null, tint = SignalCrimson)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Cancel", color = SignalCrimson)
                        }
                    }

                    if (job.status == ExportStatus.COMPLETED && !job.outputUri.isNullOrBlank()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(
                                onClick = {
                                    val intent = Intent(Intent.ACTION_VIEW).apply {
                                        setDataAndType(Uri.parse(job.outputUri), "video/mp4")
                                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                    }
                                    runCatching { context.startActivity(intent) }
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                border = BorderStroke(1.dp, HairlineBorder)
                            ) {
                                Icon(Icons.Default.PlayArrow, contentDescription = null, tint = TextPrimary)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Play", color = TextPrimary)
                            }

                            OutlinedButton(
                                onClick = {
                                    val intent = Intent(Intent.ACTION_SEND).apply {
                                        type = "video/mp4"
                                        putExtra(Intent.EXTRA_STREAM, Uri.parse(job.outputUri))
                                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                    }
                                    runCatching { context.startActivity(Intent.createChooser(intent, "Share Clip")) }
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .heightIn(min = 48.dp),
                                shape = RoundedCornerShape(12.dp),
                                border = BorderStroke(1.dp, HairlineBorder)
                            ) {
                                Icon(Icons.Default.Share, contentDescription = null, tint = TextPrimary)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Share", color = TextPrimary)
                            }
                        }
                    }
                }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/ui/screens/MainScreen.kt"] = r'''
package com.clipperzero.app.ui.screens

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.MovieFilter
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.documentfile.provider.DocumentFile
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.clipperzero.app.ui.components.AiManagerSheet
import com.clipperzero.app.ui.theme.ElevatedSurface
import com.clipperzero.app.ui.theme.HairlineBorder
import com.clipperzero.app.ui.theme.ObsidianBg
import com.clipperzero.app.ui.theme.SignalCrimson
import com.clipperzero.app.ui.theme.SignalEmerald
import com.clipperzero.app.ui.theme.SlateSurface
import com.clipperzero.app.ui.theme.TextPrimary
import com.clipperzero.app.ui.theme.TextSecondary
import com.clipperzero.app.viewmodel.AiSettingsViewModel
import com.clipperzero.app.viewmodel.DownloadsViewModel
import com.clipperzero.app.viewmodel.StudioViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    studioVm: StudioViewModel,
    downloadsVm: DownloadsViewModel,
    aiVm: AiSettingsViewModel
) {
    val context = LocalContext.current
    val studioState by studioVm.uiState.collectAsStateWithLifecycle()
    val downloadsState by downloadsVm.uiState.collectAsStateWithLifecycle()
    val jobs by downloadsVm.jobs.collectAsStateWithLifecycle()
    val aiState by aiVm.uiState.collectAsStateWithLifecycle()

    var selectedTab by remember { mutableIntStateOf(0) }
    var showAiSheet by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    val localVideoPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            }
            studioVm.handleIncomingShareOrLocal(uri.toString())
        }
    }

    val cookiesPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            studioVm.importCookies(uri)
        }
    }

    val safFolderPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            }
            val name = DocumentFile.fromTreeUri(context, uri)?.name ?: "Custom Folder"
            downloadsVm.setSafFolder(uri, name)
        }
    }

    Scaffold(
        containerColor = ObsidianBg,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(containerColor = ObsidianBg),
                title = {
                    Text(
                        text = "CLIPPER ZERO",
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp,
                        color = TextPrimary
                    )
                },
                actions = {
                    val cfg = aiState.config
                    val dotColor = when {
                        cfg.offlineMode -> TextSecondary
                        cfg.isConnected -> SignalEmerald
                        else -> SignalCrimson
                    }
                    val pillText = when {
                        cfg.offlineMode -> "No-AI"
                        cfg.isConnected -> cfg.preset.displayName
                        else -> "AI Setup"
                    }
                    Surface(
                        modifier = Modifier
                            .padding(end = 12.dp)
                            .clickable { showAiSheet = true },
                        shape = RoundedCornerShape(12.dp),
                        color = ElevatedSurface,
                        border = BorderStroke(1.dp, HairlineBorder)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Surface(
                                modifier = Modifier.size(8.dp),
                                shape = CircleShape,
                                color = dotColor
                            ) {}
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(pillText, fontSize = 12.sp, color = TextPrimary)
                        }
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar(containerColor = SlateSurface) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.MovieFilter, contentDescription = "Clip Studio") },
                    label = { Text("Clip Studio") }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.Download, contentDescription = "Downloads") },
                    label = { Text("Downloads (${jobs.size})") }
                )
            }
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            if (selectedTab == 0) {
                ClipStudioScreen(
                    state = studioState,
                    viewModel = studioVm,
                    onPickLocalVideo = { localVideoPicker.launch(arrayOf("video/*")) },
                    onPickCookiesFile = { cookiesPicker.launch(arrayOf("text/*", "*/*")) },
                    onShowSnackbar = { msg -> scope.launch { snackbarHostState.showSnackbar(msg) } }
                )
            } else {
                DownloadsScreen(
                    uiState = downloadsState,
                    jobs = jobs,
                    onSelectPreset = downloadsVm::selectStoragePreset,
                    onPickSafFolder = { safFolderPicker.launch(null) },
                    onCancelJob = downloadsVm::cancelJob,
                    onClearCompleted = downloadsVm::clearCompleted
                )
            }
        }
    }

    if (showAiSheet) {
        AiManagerSheet(
            state = aiState,
            onDismiss = { showAiSheet = false },
            onSelectPreset = aiVm::selectPreset,
            onBaseUrlChange = aiVm::updateBaseUrl,
            onPrimaryKeyChange = aiVm::updatePrimaryKey,
            onBackupKeyChange = aiVm::updateBackupKey,
            onModelChange = aiVm::updateModel,
            onModelSearchChange = aiVm::updateModelSearch,
            onOfflineToggle = aiVm::setOfflineMode,
            onRefreshModels = aiVm::refreshModels,
            onConnectProbe = aiVm::connectAndProbe
        )
    }
}
'''

FILES["app/src/main/java/com/clipperzero/app/MainActivity.kt"] = r'''
package com.clipperzero.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.clipperzero.app.ui.screens.MainScreen
import com.clipperzero.app.ui.theme.ClipperZeroTheme
import com.clipperzero.app.viewmodel.AiSettingsViewModel
import com.clipperzero.app.viewmodel.DownloadsViewModel
import com.clipperzero.app.viewmodel.StudioViewModel

class MainActivity : ComponentActivity() {

    private lateinit var studioVm: StudioViewModel
    private lateinit var downloadsVm: DownloadsViewModel
    private lateinit var aiVm: AiSettingsViewModel

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val container = (application as ClipperZeroApp).container
        val factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return when (modelClass) {
                    StudioViewModel::class.java -> StudioViewModel(container) as T
                    DownloadsViewModel::class.java -> DownloadsViewModel(container) as T
                    AiSettingsViewModel::class.java -> AiSettingsViewModel(container) as T
                    else -> throw IllegalArgumentException("Unknown ViewModel: $modelClass")
                }
            }
        }

        studioVm = ViewModelProvider(this, factory)[StudioViewModel::class.java]
        downloadsVm = ViewModelProvider(this, factory)[DownloadsViewModel::class.java]
        aiVm = ViewModelProvider(this, factory)[AiSettingsViewModel::class.java]

        requestRuntimePermissions()
        handleShareIntent(intent)

        setContent {
            ClipperZeroTheme {
                MainScreen(
                    studioVm = studioVm,
                    downloadsVm = downloadsVm,
                    aiVm = aiVm
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShareIntent(intent)
    }

    private fun handleShareIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val shared = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!shared.isNullOrBlank()) {
                studioVm.handleIncomingShareOrLocal(shared)
            }
        }
    }

    private fun requestRuntimePermissions() {
        val needed = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.POST_NOTIFICATIONS)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_VIDEO)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.READ_MEDIA_VIDEO)
            }
        } else if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.S_V2) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                needed.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }
}
'''


def main() -> None:
    sdk_dir = write_local_properties()
    if sdk_dir:
        copy_ndk_libcpp(sdk_dir)

    for rel_path, content in FILES.items():
        write_file(rel_path, content)
        print(f"Wrote {rel_path}")

    print(f"Successfully generated {len(FILES)} project files.")


if __name__ == "__main__":
    main()
    

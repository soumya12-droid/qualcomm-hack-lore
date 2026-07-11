package com.soumya.lore.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

// Lore's identity is dark by default now (ChatGPT-style near-black surfaces).
// LoreBackground/LoreSurface/etc. in Color.kt already hold the dark values,
// so this scheme just wires them into Material3's slots.
private val DarkColorScheme = darkColorScheme(
    primary = LoreEmerald,
    onPrimary = Color.White,
    secondary = LoreTextSecondary,
    background = LoreBackground,
    onBackground = LoreTextPrimary,
    surface = LoreSurface,
    onSurface = LoreTextPrimary,
    surfaceVariant = LoreBackground,
    onSurfaceVariant = LoreTextSecondary,
    outline = LoreOutline
)

// Kept for a possible future light-mode toggle — not wired up anywhere yet.
private val LightColorScheme = lightColorScheme(
    primary = LoreEmerald,
    onPrimary = Color.White,
    secondary = LoreTextSecondary,
    background = Color(0xFFFAFAF9),
    onBackground = Color(0xFF18181B),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF18181B),
    surfaceVariant = Color(0xFFFAFAF9),
    onSurfaceVariant = Color(0xFF71717A),
    outline = Color(0xFFE4E4E7)
)

@Composable
fun LoreTheme(
    // Always dark for now, regardless of system setting — this is Lore's
    // actual design, not a system-driven light/dark toggle.
    darkTheme: Boolean = true,
    // Off by default: dynamic (wallpaper-based) color would override the
    // brand palette above on Android 12+. Lore's identity is deliberate,
    // not device-dependent.
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
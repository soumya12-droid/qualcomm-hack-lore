package com.soumya.lore

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.soumya.lore.navigation.AppNavigation
import com.soumya.lore.ui.theme.LoreTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            LoreTheme {
                AppNavigation()
            }
        }
    }
}
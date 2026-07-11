package com.soumya.lore.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.soumya.lore.ui.theme.LoreOutline

/**
 * The primary search field for Lore. Deliberately larger and more rounded
 * than a default text field so it reads as the "hero" element on Home.
 *
 * The mic button is intentionally small and neutral-colored at rest — it
 * should never compete visually with search itself (see design brief:
 * "search product first, voice product second"). While recording it turns
 * emerald, matching the design system's rule that emerald marks active state.
 */
@Composable
fun LoreSearchField(
    value: String,
    onValueChange: (String) -> Unit,
    onSearch: () -> Unit,
    onMicClick: () -> Unit,
    modifier: Modifier = Modifier,
    isRecording: Boolean = false,
    isTranscribing: Boolean = false
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier
            .fillMaxWidth()
            .height(64.dp)
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp)),
        placeholder = {
            Text(
                text = "Ask Lore anything...",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        },
        leadingIcon = {
            Icon(
                imageVector = Icons.Default.Search,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        },
        trailingIcon = {
            IconButton(onClick = onMicClick, enabled = !isTranscribing) {
                if (isTranscribing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.Mic,
                        contentDescription = if (isRecording) "Stop recording" else "Voice search",
                        tint = if (isRecording) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                }
            }
        },
        singleLine = true,
        shape = RoundedCornerShape(20.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedContainerColor = MaterialTheme.colorScheme.surface,
            unfocusedContainerColor = MaterialTheme.colorScheme.surface,
            focusedBorderColor = MaterialTheme.colorScheme.primary,
            unfocusedBorderColor = LoreOutline
        ),
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        keyboardActions = KeyboardActions(onSearch = { onSearch() })
    )
}

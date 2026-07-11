package com.soumya.lore.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.soumya.lore.data.mockAnswerFor
import com.soumya.lore.ui.components.AnswerCard
import com.soumya.lore.ui.components.SourceCard
import com.soumya.lore.ui.theme.LoreTheme

/**
 * Terminal screen of the flow: Question -> Answer -> Retrieved Sources.
 * [query] is used to look up the mock answer today; later this becomes
 * the real backend response passed in the same shape.
 */
@Composable
fun ResultScreen(
    query: String,
    onBack: () -> Unit,
    onNewSearch: () -> Unit,
    modifier: Modifier = Modifier
) {
    val result = remember(query) { mockAnswerFor(query) }

    val sourceCountLabel = if (result.sources.size == 1) {
        "1 source found"
    } else {
        "${result.sources.size} sources found"
    }

    Scaffold(modifier = modifier) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
        ) {
            // --- Compact top bar (this is a sub-screen, not the entry point) ---
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp)
                    .padding(top = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBack) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = MaterialTheme.colorScheme.onBackground,
                        modifier = Modifier.size(28.dp)
                    )
                }
                Text(
                    text = "LORE",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 3.sp,
                    color = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier.padding(start = 4.dp)
                )
            }

            // --- Original query ---
            Column(
                modifier = Modifier
                    .padding(horizontal = 24.dp)
                    .padding(top = 16.dp, bottom = 20.dp)
            ) {
                Text(
                    text = "Results for",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "\"$query\"",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier.padding(top = 2.dp)
                )
            }

            // --- Answer: given a narrower horizontal inset than the rest of
            // the page, so it reads as slightly wider/more prominent ---
            AnswerCard(
                answer = result.answer,
                modifier = Modifier.padding(horizontal = 16.dp)
            )

            // --- Sources ---
            Column(modifier = Modifier.padding(horizontal = 24.dp)) {
                Text(
                    text = "Retrieved From Memory",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 32.dp)
                )
                Text(
                    text = sourceCountLabel,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
                )
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    result.sources.forEach { source ->
                        SourceCard(source = source)
                    }
                }

                Button(
                    onClick = onNewSearch,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    ),
                    modifier = Modifier
                        .padding(top = 32.dp, bottom = 24.dp)
                        .align(Alignment.CenterHorizontally)
                ) {
                    Text("New Search")
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun ResultScreenPreview() {
    LoreTheme {
        ResultScreen(query = "What papers did I read about embeddings?", onBack = {}, onNewSearch = {})
    }
}

package com.soumya.lore.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.InsertDriveFile
import androidx.compose.material.icons.outlined.PictureAsPdf
import androidx.compose.material.icons.outlined.TextSnippet
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.soumya.lore.data.Source
import com.soumya.lore.ui.theme.LoreOutline

/** Maps a file's extension to a representative icon. Falls back to a generic file icon. */
private fun iconForFileName(fileName: String): ImageVector =
    when (fileName.substringAfterLast('.', "").lowercase()) {
        "pdf" -> Icons.Outlined.PictureAsPdf
        "doc", "docx" -> Icons.Outlined.Description
        "txt", "md" -> Icons.Outlined.TextSnippet
        else -> Icons.Outlined.InsertDriveFile
    }

/**
 * One retrieved source. Deliberately plain: icon, file name, snippet — no
 * score, no percentage, no citation marker. This should read as "here's
 * where that came from," not a ranked search result.
 */
@Composable
fun SourceCard(source: Source, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, LoreOutline)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = iconForFileName(source.fileName),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(18.dp)
            )
            Column(modifier = Modifier.padding(start = 10.dp)) {
                Text(
                    text = source.fileName,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = source.snippet,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 2.dp)
                )
            }
        }
    }
}

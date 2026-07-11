package com.soumya.lore.data

import androidx.compose.ui.geometry.Offset

/**
 * One node in the knowledge-graph visualization. [position] is fractional
 * (0f..1f on each axis) so the same layout scales to any canvas size.
 * [baseRadiusScale] lets a few "hub" nodes render larger, matching the
 * varied node sizes of an organic graph rather than a uniform mesh.
 */
data class GraphNode(
    val id: Int,
    val position: Offset,
    val baseRadiusScale: Float = 1f
)

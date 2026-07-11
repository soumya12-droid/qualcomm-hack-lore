package com.soumya.lore.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationVector1D
import androidx.compose.animation.core.AnimationVector2D
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.lerp
import com.soumya.lore.data.KnowledgeGraphLayout
import com.soumya.lore.data.pathPosition

private val DIM_NODE_COLOR = Color(0xFF5A5A5A)
private val EDGE_COLOR = Color(0xFF7E7E7E)
private val MATCH_COLOR = Color(0xFFFFC94A) // gold/yellow — a "relevant match", distinct from the emerald query node
private const val EDGE_BASE_ALPHA = 0.32f
private const val NODE_BASE_RADIUS_DP = 3.5f
private const val GLOW_NODE_RADIUS_DP = 5.5f

// How far past the query node's current x-position the graph is already
// visible (a soft leading edge) and how wide the fade-in band is.
private const val REVEAL_SOFTNESS = 0.16f

/**
 * Pure rendering of the knowledge graph: light-gray edges, nodes that
 * brighten from gray to gold as [nodeGlow] rises (a "relevant match" is
 * gold — distinct from the emerald traveling query node), and a progressive
 * left-to-right reveal so only the portion of the graph near/behind the
 * query node's current position is visible; more appears as it travels.
 *
 * Every value is read directly inside the draw phase (via `.value`), so
 * animating them redraws this Canvas without recomposing it.
 */
@Composable
fun KnowledgeGraphCanvas(
    graph: KnowledgeGraphLayout,
    nodeGlow: List<Animatable<Float, AnimationVector1D>>,
    graphVisibility: Animatable<Float, AnimationVector1D>,
    queryNodeAlpha: Animatable<Float, AnimationVector1D>,
    queryNodePosition: Animatable<Offset, AnimationVector2D>,
    queryNodeRadius: Animatable<Float, AnimationVector1D>,
    lapProgress: Animatable<Float, AnimationVector1D>,
    isTraveling: Boolean,
    emeraldColor: Color,
    modifier: Modifier = Modifier
) {
    // Ratchets forward only — once part of the graph is revealed it stays
    // revealed, even if the dot's x later decreases (e.g. moving to center
    // for Stage 3). A plain mutable cell, not Compose state: it's written
    // and read purely inside the draw phase, so it must not trigger
    // recomposition itself.
    val maxRevealX = remember { floatArrayOf(0.02f) }

    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height

        val position = if (isTraveling) {
            pathPosition(graph.travelWaypoints, lapProgress.value)
        } else {
            queryNodePosition.value
        }
        if (position.x > maxRevealX[0]) maxRevealX[0] = position.x

        drawEdges(graph, graphVisibility.value, maxRevealX[0], w, h)
        drawNodes(graph, nodeGlow, graphVisibility.value, maxRevealX[0], w, h)

        if (queryNodeAlpha.value > 0f) {
            drawQueryNode(
                position = position,
                radiusDp = queryNodeRadius.value,
                alpha = queryNodeAlpha.value,
                color = emeraldColor,
                w = w,
                h = h
            )
        }
    }
}

/** 1f at/behind [revealX], fading to 0f over [REVEAL_SOFTNESS] ahead of it. */
private fun revealAlphaFor(x: Float, revealX: Float): Float =
    1f - ((x - revealX) / REVEAL_SOFTNESS).coerceIn(0f, 1f)

private fun DrawScope.drawEdges(graph: KnowledgeGraphLayout, visibility: Float, revealX: Float, w: Float, h: Float) {
    if (visibility <= 0f) return
    val nodesById = graph.nodes.associateBy { it.id }
    for (edge in graph.edges) {
        val from = nodesById[edge.fromId] ?: continue
        val to = nodesById[edge.toId] ?: continue
        val reveal = revealAlphaFor(maxOf(from.position.x, to.position.x), revealX)
        if (reveal <= 0f) continue
        drawLine(
            color = EDGE_COLOR.copy(alpha = EDGE_BASE_ALPHA * visibility * reveal),
            start = Offset(from.position.x * w, from.position.y * h),
            end = Offset(to.position.x * w, to.position.y * h),
            strokeWidth = 1.4f
        )
    }
}

private fun DrawScope.drawNodes(
    graph: KnowledgeGraphLayout,
    nodeGlow: List<Animatable<Float, AnimationVector1D>>,
    visibility: Float,
    revealX: Float,
    w: Float,
    h: Float
) {
    if (visibility <= 0f) return
    graph.nodes.forEachIndexed { index, node ->
        val reveal = revealAlphaFor(node.position.x, revealX)
        if (reveal <= 0f) return@forEachIndexed

        val glow = nodeGlow.getOrNull(index)?.value ?: 0f
        val color = lerp(DIM_NODE_COLOR, MATCH_COLOR, glow)
        val radius = dp(
            (NODE_BASE_RADIUS_DP + (GLOW_NODE_RADIUS_DP - NODE_BASE_RADIUS_DP) * glow) * node.baseRadiusScale
        )
        val center = Offset(node.position.x * w, node.position.y * h)
        val alphaMultiplier = visibility * reveal

        if (glow > 0.05f) {
            // Soft glow: a few translucent rings behind the solid node,
            // cheaper than a blur and avoids any "particle" feel.
            drawCircle(color = color.copy(alpha = 0.18f * glow * alphaMultiplier), radius = radius * 2.4f, center = center)
            drawCircle(color = color.copy(alpha = 0.30f * glow * alphaMultiplier), radius = radius * 1.6f, center = center)
        }
        drawCircle(color = color.copy(alpha = (0.35f + 0.65f * glow) * alphaMultiplier), radius = radius, center = center)
    }
}

private fun DrawScope.drawQueryNode(
    position: Offset,
    radiusDp: Float,
    alpha: Float,
    color: Color,
    w: Float,
    h: Float
) {
    val center = Offset(position.x * w, position.y * h)
    val radius = dp(radiusDp)
    drawCircle(color = color.copy(alpha = 0.16f * alpha), radius = radius * 3f, center = center)
    drawCircle(color = color.copy(alpha = 0.28f * alpha), radius = radius * 1.9f, center = center)
    drawCircle(color = color.copy(alpha = alpha), radius = radius, center = center)
}

private fun DrawScope.dp(value: Float): Float = value * density

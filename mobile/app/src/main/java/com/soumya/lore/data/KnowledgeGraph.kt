package com.soumya.lore.data

import androidx.compose.ui.geometry.Offset
import kotlin.math.sqrt
import kotlin.random.Random

/**
 * Everything the loading-screen animation needs to draw and animate a
 * knowledge graph. Generated once with a fixed seed and [remember]ed by the
 * caller — node positions never move or regenerate mid-animation, per the
 * "no random movement" requirement.
 */
data class KnowledgeGraphLayout(
    val nodes: List<GraphNode>,
    val edges: List<GraphEdge>,
    /**
     * The 3-5 nodes that light up because they sit near the travel path —
     * paired with how far along the path (0f..1f) each one is, so the
     * lighting sequence can fire in the same left-to-right order the dot
     * actually travels.
     */
    val relevantNodePlan: List<Pair<Int, Float>>,
    /** Fractional waypoints the query node travels through, left to right. */
    val travelWaypoints: List<Offset>
)

private const val SEED = 2024L
private const val CLUSTER_COUNT = 5
private const val NODES_PER_CLUSTER_MIN = 4
private const val NODES_PER_CLUSTER_MAX = 6
private const val CLUSTER_SPREAD = 0.10f
private const val MIN_NODE_SEPARATION = 0.045f
private const val RELEVANT_NODE_COUNT = 4
private const val PATH_SAMPLE_COUNT = 60

/**
 * Builds a stable, organic, tightly-clustered layout — a handful of loose
 * local clusters (short edges within, matching a real notes-graph look)
 * bridged by a few longer connecting lines, rather than one sparse mesh.
 */
fun generateKnowledgeGraph(): KnowledgeGraphLayout {
    val random = Random(SEED)

    val clusterCenters = (0 until CLUSTER_COUNT).map { i ->
        val x = (i + 0.5f) / CLUSTER_COUNT
        val y = 0.28f + random.nextFloat() * 0.44f
        Offset(x, y)
    }

    val clusters = clusterCenters.map { center -> scatterCluster(center, random) }
    val points = clusters.flatten()

    // Global index ranges for each cluster, so edge-building can stay local.
    val clusterRanges = mutableListOf<IntRange>()
    var cursor = 0
    for (cluster in clusters) {
        clusterRanges += cursor until (cursor + cluster.size)
        cursor += cluster.size
    }

    val hubIndices = clusterRanges.mapIndexed { i, range ->
        range.minBy { distance(points[it], clusterCenters[i]) }
    }.toSet()

    val nodes = points.mapIndexed { index, position ->
        GraphNode(
            id = index,
            position = position,
            baseRadiusScale = if (index in hubIndices) 1.4f else 1f
        )
    }

    val edges = buildEdges(points, clusterRanges, hubIndices, random)
    val relevantNodePlan = pickRelevantNodes(points, clusterCenters)

    return KnowledgeGraphLayout(nodes, edges, relevantNodePlan, clusterCenters)
}

private fun scatterCluster(center: Offset, random: Random): List<Offset> {
    val count = NODES_PER_CLUSTER_MIN + random.nextInt(NODES_PER_CLUSTER_MAX - NODES_PER_CLUSTER_MIN + 1)
    val clusterPoints = mutableListOf<Offset>()
    var attempts = 0
    while (clusterPoints.size < count && attempts < count * 200) {
        attempts++
        val angle = random.nextFloat() * (2 * Math.PI).toFloat()
        val radius = random.nextFloat() * CLUSTER_SPREAD
        val candidate = Offset(
            x = (center.x + kotlin.math.cos(angle) * radius).coerceIn(0.04f, 0.96f),
            y = (center.y + kotlin.math.sin(angle) * radius).coerceIn(0.08f, 0.90f)
        )
        if (clusterPoints.none { distance(it, candidate) < MIN_NODE_SEPARATION }) {
            clusterPoints += candidate
        }
    }
    return clusterPoints
}

private fun buildEdges(
    points: List<Offset>,
    clusterRanges: List<IntRange>,
    hubIndices: Set<Int>,
    random: Random
): List<GraphEdge> {
    val edgeKeys = mutableSetOf<Long>()
    val edges = mutableListOf<GraphEdge>()

    fun tryAddEdge(a: Int, b: Int) {
        if (a == b) return
        val key = if (a < b) a.toLong() * 10_000 + b else b.toLong() * 10_000 + a
        if (edgeKeys.add(key)) edges += GraphEdge(a, b)
    }

    // Within each cluster: the hub connects to every other node (short
    // star edges), plus a couple of nearest-neighbor chain edges among the
    // non-hub nodes so it doesn't read as a pure star.
    for (range in clusterRanges) {
        val hub = range.first { it in hubIndices }
        for (index in range) {
            if (index != hub) tryAddEdge(hub, index)
        }
        for (index in range) {
            if (index == hub) continue
            val nearest = range
                .filter { it != index && it != hub }
                .minByOrNull { distance(points[it], points[index]) }
                ?: continue
            if (distance(points[nearest], points[index]) < CLUSTER_SPREAD * 0.9f) {
                tryAddEdge(index, nearest)
            }
        }
    }

    // Bridge consecutive clusters with a single edge between their closest pair.
    for (i in 0 until clusterRanges.size - 1) {
        var bestPair: Pair<Int, Int>? = null
        var bestDistance = Float.MAX_VALUE
        for (a in clusterRanges[i]) {
            for (b in clusterRanges[i + 1]) {
                val d = distance(points[a], points[b])
                if (d < bestDistance) {
                    bestDistance = d
                    bestPair = a to b
                }
            }
        }
        bestPair?.let { (a, b) -> tryAddEdge(a, b) }
    }

    // A couple of extra long-range links for organic richness.
    repeat(3) {
        val a = random.nextInt(points.size)
        val b = random.nextInt(points.size)
        tryAddEdge(a, b)
    }

    return edges
}

/** The nodes geometrically closest to the travel path, in left-to-right order. */
private fun pickRelevantNodes(points: List<Offset>, waypoints: List<Offset>): List<Pair<Int, Float>> {
    val pathSamples = (0..PATH_SAMPLE_COUNT).map { i ->
        val t = i / PATH_SAMPLE_COUNT.toFloat()
        t to pathPosition(waypoints, t)
    }

    val closest = points.indices
        .map { index ->
            val (t, _) = pathSamples.minBy { (_, samplePos) -> distance(samplePos, points[index]) }
            val dist = pathSamples.minOf { (_, samplePos) -> distance(samplePos, points[index]) }
            Triple(index, t, dist)
        }
        .sortedBy { (_, _, dist) -> dist }
        .take(RELEVANT_NODE_COUNT)

    return closest.map { (index, t, _) -> index to t }.sortedBy { it.second }
}

private fun distance(a: Offset, b: Offset): Float {
    val dx = a.x - b.x
    val dy = a.y - b.y
    return sqrt(dx * dx + dy * dy)
}

/**
 * Position along the travel path at progress [t] (0f..1f, no wrap-around —
 * this is a single left-to-right traversal, not a loop). Each segment is a
 * quadratic Bézier with an alternating perpendicular bulge for a gentle
 * zigzag curve rather than straight lines.
 */
fun pathPosition(waypoints: List<Offset>, t: Float): Offset {
    val segmentCount = waypoints.size - 1
    if (segmentCount <= 0) return waypoints.firstOrNull() ?: Offset.Zero

    val clampedT = t.coerceIn(0f, 1f)
    val scaled = clampedT * segmentCount
    val segmentIndex = scaled.toInt().coerceIn(0, segmentCount - 1)
    val localT = (scaled - segmentIndex).coerceIn(0f, 1f)

    val p0 = waypoints[segmentIndex]
    val p1 = waypoints[segmentIndex + 1]
    val midX = (p0.x + p1.x) / 2f
    val midY = (p0.y + p1.y) / 2f
    val dx = p1.x - p0.x
    val dy = p1.y - p0.y
    val curveSign = if (segmentIndex % 2 == 0) 1f else -1f
    val controlX = midX - dy * 0.18f * curveSign
    val controlY = midY + dx * 0.18f * curveSign

    val inv = 1f - localT
    val x = inv * inv * p0.x + 2 * inv * localT * controlX + localT * localT * p1.x
    val y = inv * inv * p0.y + 2 * inv * localT * controlY + localT * localT * p1.y
    return Offset(x, y)
}

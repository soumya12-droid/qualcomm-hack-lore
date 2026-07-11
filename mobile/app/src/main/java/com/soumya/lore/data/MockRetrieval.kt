package com.soumya.lore.data

import kotlinx.coroutines.delay

/**
 * Stands in for the real backend round-trip. This is the ONLY thing that
 * will need to change once a real backend exists — swap this delay for
 * awaiting the actual network response. The Loading screen's animation
 * loops independently of this and simply reacts when it completes.
 */
suspend fun awaitMockSearch() {
    delay(4200)
}

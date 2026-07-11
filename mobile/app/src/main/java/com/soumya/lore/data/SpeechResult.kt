package com.soumya.lore.data

/** UI-facing outcome of a transcription attempt — the network layer never leaks raw JSON past this. */
sealed class SpeechResult {
    data class Success(val transcript: String) : SpeechResult()
    data class Error(val message: String) : SpeechResult()
}

package com.soumya.lore.data

/** UI-facing shape of a single retrieved source. Mock content until backend exists. */
data class Source(
    val fileName: String,
    val snippet: String
)

data class AnswerResult(
    val answer: String,
    val sources: List<Source>
)

/** Temporary stand-in for a real backend call. */
fun mockAnswerFor(query: String): AnswerResult = AnswerResult(
    answer = "Based on your indexed files, here's what I found related to " +
        "\"$query\". This is placeholder text until the PC and Cloud AI 100 " +
        "pipeline is connected.",
    sources = listOf(
        Source(
            fileName = "Q3_Planning_Notes.docx",
            snippet = "...relevant excerpt mentioning \"$query\" would appear here..."
        ),
        Source(
            fileName = "research-paper.pdf",
            snippet = "...another matching excerpt would appear here..."
        ),
        Source(
            fileName = "meeting-summary.txt",
            snippet = "...a third matching excerpt would appear here..."
        )
    )
)

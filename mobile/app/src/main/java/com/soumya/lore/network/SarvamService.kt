package com.soumya.lore.network

import com.soumya.lore.BuildConfig
import com.soumya.lore.data.SpeechResult
import java.io.File
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject

/**
 * Talks to Sarvam AI's Speech-to-Text REST endpoint. Verified against
 * https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe —
 * auth is the `api-subscription-key` header (not Bearer), and the REST
 * endpoint caps audio at 30 seconds per request.
 */
object SarvamService {

    private const val ENDPOINT = "https://api.sarvam.ai/speech-to-text"

    suspend fun transcribeAudio(audioFile: File): SpeechResult = withContext(Dispatchers.IO) {
        if (BuildConfig.SARVAM_API_KEY.isBlank()) {
            return@withContext SpeechResult.Error(
                "Voice search isn't set up yet — add SARVAM_API_KEY to local.properties."
            )
        }

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",
                audioFile.name,
                audioFile.asRequestBody("audio/mp4".toMediaType())
            )
            .addFormDataPart("model", "saarika:v2.5")
            .addFormDataPart("language_code", "unknown")
            .build()

        val request = Request.Builder()
            .url(ENDPOINT)
            .addHeader("api-subscription-key", BuildConfig.SARVAM_API_KEY)
            .post(requestBody)
            .build()

        try {
            NetworkModule.client.newCall(request).execute().use { response ->
                val bodyString = response.body?.string().orEmpty()

                if (!response.isSuccessful) {
                    return@withContext SpeechResult.Error(errorMessageFor(response.code))
                }

                val transcript = JSONObject(bodyString).optString("transcript").trim()
                if (transcript.isEmpty()) {
                    SpeechResult.Error("Didn't catch that — try speaking again.")
                } else {
                    SpeechResult.Success(transcript)
                }
            }
        } catch (_: IOException) {
            SpeechResult.Error("Check your connection and try again.")
        } catch (_: org.json.JSONException) {
            SpeechResult.Error("Something went wrong understanding that. Try again.")
        }
    }

    private fun errorMessageFor(code: Int): String = when (code) {
        401, 403 -> "Voice search is unavailable right now."
        413 -> "That recording was too long — try a shorter question."
        429 -> "Too many requests — wait a moment and try again."
        else -> "Couldn't transcribe that — try again."
    }
}

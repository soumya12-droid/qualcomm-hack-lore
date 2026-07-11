package com.soumya.lore.ui.screens

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.soumya.lore.audio.AudioRecorder
import com.soumya.lore.data.SpeechResult
import com.soumya.lore.network.SarvamService
import java.io.IOException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Everything HomeScreen needs to know about voice input — nothing more. */
sealed class VoiceState {
    data object Idle : VoiceState()
    data object Recording : VoiceState()
    data object Transcribing : VoiceState()
    data class Transcribed(val transcript: String) : VoiceState()
    data class Error(val message: String) : VoiceState()
}

/**
 * Owns the mic → record → transcribe flow so HomeScreen never touches
 * MediaRecorder, OkHttp, or the Sarvam response shape directly. Survives
 * recomposition and configuration changes, which matters here since a
 * network call can outlive a single Compose frame.
 */
class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val audioRecorder = AudioRecorder(application.applicationContext)

    private val _voiceState = MutableStateFlow<VoiceState>(VoiceState.Idle)
    val voiceState: StateFlow<VoiceState> = _voiceState.asStateFlow()

    /** Call when the mic button is tapped while the permission is already granted. */
    fun onMicPressed() {
        if (_voiceState.value is VoiceState.Recording) {
            stopAndTranscribe()
        } else {
            startRecording()
        }
    }

    fun onPermissionDenied() {
        _voiceState.value = VoiceState.Error("Microphone permission is needed for voice search.")
    }

    /** Call once the transcript has been read into the search field. */
    fun consumeTranscript() {
        _voiceState.value = VoiceState.Idle
    }

    /** Call once an error message has been shown to the user. */
    fun dismissError() {
        _voiceState.value = VoiceState.Idle
    }

    private fun startRecording() {
        try {
            audioRecorder.start()
            _voiceState.value = VoiceState.Recording
        } catch (e: IOException) {
            _voiceState.value = VoiceState.Error("Couldn't start recording. Try again.")
        }
    }

    private fun stopAndTranscribe() {
        val file = audioRecorder.stop()
        if (file == null) {
            _voiceState.value = VoiceState.Error("Recording was too short — try again.")
            return
        }

        _voiceState.value = VoiceState.Transcribing
        viewModelScope.launch {
            when (val result = SarvamService.transcribeAudio(file)) {
                is SpeechResult.Success -> _voiceState.value = VoiceState.Transcribed(result.transcript)
                is SpeechResult.Error -> _voiceState.value = VoiceState.Error(result.message)
            }
            file.delete()
        }
    }

    override fun onCleared() {
        audioRecorder.cancel()
        super.onCleared()
    }
}

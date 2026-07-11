package com.soumya.lore.network

import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient

/** One OkHttpClient for the whole app — connection pooling means we never want more than this. */
object NetworkModule {
    val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }
}

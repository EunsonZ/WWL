package org.wwl.networkdemo

import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import javax.net.ssl.SSLHandshakeException
import javax.net.ssl.SSLPeerUnverifiedException

/** Independent native checks of the unchanged actual HttpsTransport and generated debug CA. */
class GeneratedTlsContractTest {
    private fun observed(value: String) {
        InstrumentationRegistry.getInstrumentation().sendStatus(0,
            android.os.Bundle().apply { putString("stream", value + "\n") })
    }
    @Test fun generatedCaTrustedByActualTransport() {
        val response = HttpsTransport("D").snapshot("self")
        assertEquals("wwl-reservation-v2/1", response.getString("protocol"))
        assertEquals(3, response.getJSONArray("bookings").length())
        observed("generated CA positive: actual HttpsTransport HTTPS snapshot and three seeds")
    }
    @Test fun sameCaWrongHostnameRejected() {
        try {
            HttpsTransport("D").snapshot("self")
            fail("same-CA wrong hostname accepted")
        } catch (error: SSLPeerUnverifiedException) {
            assertTrue(error.message.orEmpty().contains("Hostname 127.0.0.1 not verified"))
            observed("same-CA wrong hostname: " + error.javaClass.simpleName + " " + error.message)
        }
    }
    @Test fun differentCaWithCorrectNameRejected() {
        try {
            HttpsTransport("D").snapshot("self")
            fail("different CA accepted")
        } catch (error: SSLHandshakeException) {
            val messages = generateSequence<Throwable>(error) { it.cause }
                .joinToString(" | ") { it.message.orEmpty() }
            assertTrue(messages, messages.contains("Trust anchor for certification path not found"))
            observed("different CA/correct SAN: " + error.javaClass.simpleName + " " + messages)
        }
    }
}

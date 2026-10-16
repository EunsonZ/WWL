package org.wwl.intentdemo
import org.junit.Assert.*
import org.junit.Test

class ProtocolTest {
    @Test fun canonicalKnownValue() {
        assertEquals("{\"actor\":\"D\",\"end\":720,\"op\":\"reserve\",\"policy_version\":2,\"start\":690}", Protocol.canonical("D",690,720))
        assertEquals("d644656f03ece17dcce05e3855ec43ae1c4b50186e8b58c631c77ed2f846a867", Protocol.fingerprint("D",690,720))
        assertNotEquals(Protocol.fingerprint("D",690,720),Protocol.fingerprint("D",700,730))
    }
    @Test fun intervalAndBuffer() {
        assertTrue(Protocol.validInterval(690,720));assertFalse(Protocol.validInterval(690,719))
        assertTrue(Protocol.compatible(690,720,650,680));assertFalse(Protocol.compatible(680,710,650,680))
        assertFalse(Protocol.validInterval(Int.MIN_VALUE,Int.MAX_VALUE))
    }
    @Test fun textAndEscaping() {
        assertEquals("\"中😀\\n\\\"\\\\\"",Protocol.quote("中😀\n\"\\"))
        assertEquals("😀".repeat(128),Protocol.text("😀".repeat(128)))
        for (s in listOf("", " ", "\u0085", "x".repeat(129), "\uD800")) {
            try { Protocol.text(s);fail("expected invalid input") } catch (_: IllegalArgumentException) {}
        }
    }
}

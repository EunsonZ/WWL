package org.wwl.intentdemo

import java.security.MessageDigest

/** Same canonical fields/UTF8 as SE82. This is a parameter checksum, not authentication. */
object Protocol {
    const val NAME = "wwl-reservation-v2/1"
    fun text(value: String): String {
        val count = value.codePointCount(0, value.length)
        // Python str.isspace additionally includes NEL and the four record separators.
        require(count in 1..128 && value.codePoints().anyMatch { cp ->
            !(Character.isWhitespace(cp) || Character.isSpaceChar(cp) || cp == 0x85 || cp in 0x1c..0x1f)
        }) { "nonblank text up to 128 Unicode codepoints required" }
        require(value.indices.none { i -> Character.isSurrogate(value[i]) &&
            !(Character.isHighSurrogate(value[i]) && i+1 < value.length && Character.isLowSurrogate(value[i+1])) &&
            !(Character.isLowSurrogate(value[i]) && i>0 && Character.isHighSurrogate(value[i-1])) }) { "valid Unicode scalar sequence required" }
        return value
    }
    fun quote(value: String): String = buildString {
        append('"')
        for (c in value) when(c) {
            '"' -> append("\\\""); '\\' -> append("\\\\")
            '\b' -> append("\\b"); '\u000c' -> append("\\f"); '\n' -> append("\\n"); '\r' -> append("\\r"); '\t' -> append("\\t")
            else -> if(c.code < 32) append("\\u%04x".format(c.code)) else append(c)
        }
        append('"')
    }
    fun canonical(actor: String, start: Int, end: Int, policy: Int = 2): String {
        text(actor)
        return "{\"actor\":" + quote(actor) + ",\"end\":$end,\"op\":\"reserve\",\"policy_version\":$policy,\"start\":$start}"
    }
    fun fingerprint(actor: String, start: Int, end: Int, policy: Int = 2): String =
        MessageDigest.getInstance("SHA-256").digest(canonical(actor,start,end,policy).toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it.toInt() and 255) }
    fun validInterval(start: Int, end: Int): Boolean = start >= 540 && end <= 1020 && end > start && end.toLong()-start in 30L..120L
    fun compatible(start: Int, end: Int, oldStart: Int, oldEnd: Int): Boolean =
        end.toLong()+10 <= oldStart || oldEnd.toLong()+10 <= start
}

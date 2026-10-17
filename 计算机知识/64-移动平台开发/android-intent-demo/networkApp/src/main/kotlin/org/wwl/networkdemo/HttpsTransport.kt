package org.wwl.networkdemo

import org.json.JSONObject
import org.wwl.intentdemo.Pending
import org.wwl.intentdemo.Protocol
import java.io.IOException
import java.net.URL
import java.net.URLEncoder
import javax.net.ssl.HttpsURLConnection

class HttpFailure(val code:Int):IOException("HTTP $code; no new business decision inferred")

/** Default platform TLS/hostname verification; app's DEBUG resource adds only its lab CA. */
class HttpsTransport(private val actor:String,private val network:android.net.Network?=null) {
    private val cancelled=java.util.concurrent.atomic.AtomicBoolean(false)
    private val active=java.util.concurrent.atomic.AtomicReference<HttpsURLConnection?>(null)
    /** Instance cancellation is used only by a bounded JobService attempt. Call off main. */
    fun cancel() { cancelled.set(true);active.getAndSet(null)?.disconnect() }
    private val endpoint="https://127.0.0.1:18751"
    private fun token(mode:String):String = when(mode) {
        "self" -> "wwl175-public-$actor"
        "other" -> "wwl175-public-${if(actor=="D")"E" else "D"}"
        "invalid" -> "deliberately-invalid-public-fixture"
        else -> throw IllegalArgumentException("credential mode")
    }
    private fun request(path:String,mode:String,body:JSONObject?=null,drop:Boolean=false):JSONObject {
        if(cancelled.get())throw java.io.InterruptedIOException("job stopped before connection")
        val url=URL(endpoint+path)
        val connection=(network?.openConnection(url)?:url.openConnection()) as HttpsURLConnection
        active.set(connection)
        try {
            if(cancelled.get())throw java.io.InterruptedIOException("job stopped during connection setup")
            connection.instanceFollowRedirects=false
            connection.connectTimeout=1500;connection.readTimeout=2000
            connection.requestMethod=if(body==null)"GET" else "POST"
            connection.setRequestProperty("Authorization","Bearer ${token(mode)}")
            connection.setRequestProperty("Accept","application/json")
            connection.setRequestProperty("Connection","close")
            if(drop) { require(BuildConfig.DEBUG);connection.setRequestProperty("X-WWL-Lab-Drop-Reply","true") }
            if(body!=null) {
                val bytes=body.toString().toByteArray(Charsets.UTF_8)
                connection.doOutput=true
                connection.setRequestProperty("Content-Type","application/json; charset=utf-8")
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.outputStream.use { it.write(bytes) }
            }
            val code=connection.responseCode
            if(code!=200)throw HttpFailure(code) // Includes 3xx; never forward Bearer to redirects.
            if(connection.contentType?.substringBefore(';')?.trim()!="application/json")throw IOException("content type")
            val bytes=connection.inputStream.use { input ->
                val output=java.io.ByteArrayOutputStream();val buffer=ByteArray(4096)
                while(output.size()<=65536) {
                    val n=input.read(buffer,0,minOf(buffer.size,65537-output.size()))
                    if(n<0)break
                    output.write(buffer,0,n)
                }
                output.toByteArray()
            }
            if(bytes.size>65536)throw IOException("response too large")
            return JSONObject(String(bytes,Charsets.UTF_8))
        } finally { active.compareAndSet(connection,null);connection.disconnect() }
    }
    fun snapshot(mode:String)=request("/v2/snapshot",mode)
    fun query(p:Pending,mode:String):JSONObject {
        fun encoded(s:String)=URLEncoder.encode(s,"UTF-8")
        return request("/v2/intent?intent_id=${encoded(p.id)}&fingerprint=${encoded(p.fp)}",mode)
    }
    fun reserve(p:Pending,mode:String,drop:Boolean=false):JSONObject {
        require(p.actor==actor)
        val b=JSONObject().put("protocol",Protocol.NAME).put("actor",p.actor).put("intent_id",p.id)
            .put("start",p.start).put("end",p.end).put("fingerprint",p.fp).put("policy_version",2)
        return request("/v2/reserve",mode,b,drop)
    }
}

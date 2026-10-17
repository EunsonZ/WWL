package org.wwl.networkdemo

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.util.AtomicFile
import org.json.JSONObject
import org.wwl.intentdemo.ClientStore
import org.wwl.intentdemo.Pending
import org.wwl.intentdemo.Protocol
import java.io.File
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit

class NetworkApp:Application() {
    lateinit var repository:NetworkRepository
        private set
    override fun onCreate() { super.onCreate();repository=NetworkRepository(this) }
}

/** One process worker; service authority is outside both app sandboxes. No MockAuthority instance. */
class NetworkRepository(private val app:Application) {
    val worker=ScheduledThreadPoolExecutor(1)
    val client=ClientStore(app)
    private val main=Handler(Looper.getMainLooper())
    private val transport=HttpsTransport(BuildConfig.ACTOR)
    private val projection=AtomicFile(File(app.filesDir,"projection.json"))
    private val credential=AtomicFile(File(app.filesDir,"credential-mode.txt"))
    private var hint="尚未联网。缓存不是容量承诺。"
    private fun atomic(file:AtomicFile,bytes:ByteArray) {
        val out=file.startWrite()
        try { out.write(bytes);file.finishWrite(out) } catch(e:Exception) { file.failWrite(out);throw e }
    }
    private fun mode():String = if(credential.baseFile.exists())String(credential.readFully(),Charsets.UTF_8).also {
        require(it in setOf("self","other","invalid"))
    } else "self"
    init { worker.execute { client.recoverInflight();exportState() } }
    fun audit(kind:String,detail:String) { worker.execute { client.audit(kind,detail);exportState() } }
    fun exportState():JSONObject {
        val cached=if(projection.baseFile.exists())JSONObject(String(projection.readFully(),Charsets.UTF_8)) else JSONObject.NULL
        val state=JSONObject().put("pid",Process.myPid()).put("uid",Process.myUid()).put("actor",BuildConfig.ACTOR)
            .put("client",client.snapshot()).put("projection",cached).put("credential_mode",mode()).put("transport_hint",hint)
        atomic(AtomicFile(File(app.filesDir,"network-state.json")),state.toString(2).toByteArray(Charsets.UTF_8))
        return state
    }
    fun recordUi(value:JSONObject) { worker.execute {
        atomic(AtomicFile(File(app.filesDir,"network-ui.json")),value.toString(2).toByteArray(Charsets.UTF_8));exportState()
    } }
    fun refresh(callback:(JSONObject)->Unit) { worker.execute { val s=exportState();main.post { callback(s) } } }
    private fun work(callback:(Result<JSONObject>)->Unit,block:()->Unit) { worker.execute {
        val r=runCatching { block();exportState() };main.post { callback(r) }
    } }
    fun queue(start:Int,end:Int,id:String,callback:(Result<JSONObject>)->Unit)=work(callback) {
        client.queue(BuildConfig.ACTOR,id,start,end);hint="只在本机落盘；未访问服务。"
    }
    fun saveDraft(start:String,end:String,callback:(Result<JSONObject>)->Unit)=work(callback) { client.saveDraft(start,end) }
    fun credential(mode:String,callback:(Result<JSONObject>)->Unit)=work(callback) {
        require(mode in setOf("self","other","invalid"))
        atomic(credential,mode.toByteArray(Charsets.UTF_8));hint="切换公开测试凭据：$mode；未改变业务actor/id。"
    }
    fun fetch(callback:(Result<JSONObject>)->Unit)=work(callback) {
        try {
            val raw=transport.snapshot(mode());require(raw.getString("protocol")==Protocol.NAME)
            val rows=raw.getJSONArray("bookings")
            for(i in 0 until rows.length()) {
                val b=rows.getJSONObject(i)
                for(k in listOf("id","start","end","policy_version"))require(b.get(k) is Int||b.get(k) is Long)
                require(b.getLong("id")>0);Protocol.text(b.get("owner") as String)
                val s=b.getLong("start");val e=b.getLong("end")
                require(s in 540..1020&&e-s in 30..120&&e<=1020)
                require(b.getLong("policy_version") in 1..2)
            }
            // Only one in-process worker; receive time is local metadata, NOT a service version.
            atomic(projection,JSONObject().put("snapshot",raw).put("received_at_ms",System.currentTimeMillis()).toString().toByteArray(Charsets.UTF_8))
            hint="已取服务投影；它可能随后过时，仍不预留容量。"
        } catch(e:Exception) { hint=describe(e);client.audit("projection_failed",hint) }
    }
    private fun describe(e:Exception):String = if(e is HttpFailure)"HTTP ${e.code}：未据此改判业务；保留原id。" else "传输/校验失败 ${e.javaClass.simpleName}：结果可能未知，保留原id。"
    private fun unknown(p:Pending,r:JSONObject):Boolean {
        require(r.get("protocol")==Protocol.NAME&&r.get("actor")==p.actor&&r.get("intent_id")==p.id)
        if(r.optString("status")!="unknown")return false
        require(r.keys().asSequence().toSet()==setOf("protocol","actor","intent_id","status","reason"))
        require(r.get("reason")=="not_registered")
        return true
    }
    fun attempt(actor:String,id:String,operation:String,callback:(String,Result<JSONObject>)->Unit) {
        require(operation in setOf("send","drop","recover","query","delay"))
        worker.execute {
            val key="$actor\u0000$id"
            val result=runCatching {
                require(actor==BuildConfig.ACTOR)
                val p=client.get(actor,id)?:error("no persisted intent")
                client.phase(p,"sending");client.audit("https_attempt",p.id+":"+operation);exportState()
                var response:JSONObject?=null
                try {
                    val m=mode()
                    response=when(operation) {
                        "query","recover" -> transport.query(p,m).let { q ->
                            if(unknown(p,q)) {
                                if(operation=="recover")transport.reserve(p,m) else null
                            } else q
                        }
                        else -> transport.reserve(p,m,operation=="drop")
                    }
                    if(response==null) { client.phase(p,"unknown");hint="查询尚未登记；不是终局拒绝。" }
                } catch(e:Exception) {
                    client.phase(p,if(e is HttpFailure&&e.code==409)"protocol_error" else "unknown")
                    hint=describe(e);client.audit("https_uncertain",hint)
                }
                val reply=response
                if(reply!=null) {
                    // Persist an authenticated response only into its original row.
                    if(operation=="delay") {
                        client.audit("local_reply_held",p.id);exportState()
                        worker.schedule({
                            val delayed=runCatching { client.accept(p,reply);hint="原回复已入原行；请核UI发布门。";exportState() }
                            if(delayed.isFailure) { client.phase(p,"protocol_error");exportState() }
                            main.post { callback(key,delayed) }
                        },3,TimeUnit.SECONDS)
                        return@execute
                    }
                    try { client.accept(p,reply);hint="服务终局已核身份并保存。" }
                    catch(e:Exception) { client.phase(p,"protocol_error");hint="业务响应校验失败；原记录保留。";throw e }
                }
                exportState()
            }
            main.post { callback(key,result) }
        }
    }
}

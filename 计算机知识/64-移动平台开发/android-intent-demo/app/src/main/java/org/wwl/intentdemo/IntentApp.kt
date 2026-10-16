package org.wwl.intentdemo

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.os.Process
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Callable
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit

class IntentApp:Application() {
    lateinit var repository:Repository
        private set
    override fun onCreate() { super.onCreate();repository=Repository(this) }
}

class Repository(private val app:Application) {
    val worker=ScheduledThreadPoolExecutor(1)
    val client=ClientStore(app)
    val authority=MockAuthority(app)
    private val main=Handler(Looper.getMainLooper())
    init { worker.execute { client.recoverInflight();authority.readableDatabase;exportState() } }
    fun <T> blocking(block:Repository.()->T):T { check(Looper.myLooper()!=Looper.getMainLooper());return worker.submit(Callable { block(this) }).get(15,TimeUnit.SECONDS) }
    fun audit(kind:String,detail:String) { worker.execute { client.audit(kind,detail);exportState() } }
    fun exportState():JSONObject {
        val state=JSONObject().put("pid",Process.myPid()).put("client",client.snapshot()).put("mock_authority",authority.snapshot())
        File(app.filesDir,"store-state.json").writeText(state.toString(2));return state
    }
    fun recordUi(value:JSONObject) { worker.execute { File(app.filesDir,"ui-state.json").writeText(value.toString(2));exportState() } }
    fun refresh(callback:(JSONObject)->Unit) { worker.execute { val s=exportState();main.post { callback(s) } } }
    fun queue(start:Int,end:Int,id:String,callback:(Result<JSONObject>)->Unit) { worker.execute {
        val r=runCatching { client.queue("D",id,start,end);exportState() };main.post { callback(r) }
    } }
    fun saveDraft(start:String,end:String,callback:(Result<JSONObject>)->Unit) { worker.execute {
        val r=runCatching { client.saveDraft(start,end);client.audit("draft_saved","explicit action");exportState() };main.post { callback(r) }
    } }
    fun attempt(actor:String,id:String,mode:String,callback:(String,Result<JSONObject>)->Unit) {
        require(mode in setOf("normal","drop","before","delay","recover"))
        worker.execute {
            val p=client.get(actor,id) ?: run { main.post { callback("$actor\u0000$id",Result.failure(IllegalStateException("missing persisted intent"))) };return@execute }
            var response:JSONObject?=null
            val error=runCatching {
                client.phase(p,"sending");client.audit("send_same_identity",p.id)
                if(mode=="recover") {
                    response=authority.query(p.actor,p.id,p.fp)
                    if(response!!.getString("status")=="unknown")response=authority.reserve(p)
                } else response=authority.reserve(p,beforeCommit=mode=="before")
                if(mode=="drop")throw java.io.IOException("lab committed reply lost")
            }.exceptionOrNull()
            if(error!=null) {
                client.phase(p,"unknown");client.audit("attempt_uncertain",p.id);val state=exportState()
                main.post { callback(p.key,Result.success(state)) };return@execute
            }
            val deliver={
                val result=runCatching { client.accept(p,response!!);exportState() }
                if(result.isFailure) { client.phase(p,"protocol_error");exportState() }
                main.post { callback(p.key,result) }
            }
            if(mode=="delay") {
                client.audit("reply_held",p.id);exportState()
                worker.schedule({ deliver() },3,TimeUnit.SECONDS)
            } else deliver()
        }
    }
}

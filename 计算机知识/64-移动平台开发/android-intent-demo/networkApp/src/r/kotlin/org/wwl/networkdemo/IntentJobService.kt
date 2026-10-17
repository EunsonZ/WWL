package org.wwl.networkdemo

import android.app.job.JobParameters
import android.app.job.JobService
import android.os.Build
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import org.wwl.intentdemo.Pending
import org.wwl.intentdemo.Protocol
import java.util.concurrent.atomic.AtomicBoolean

/** Persisted JobScheduler metadata points to a durable intent; it never invents one. */
class IntentJobService:JobService() {
    private class Run(val params:JobParameters) {
        val stopped=AtomicBoolean(false)
        @Volatile var transport:HttpsTransport?=null
    }
    private var active:Run?=null
    private val app:ResourceApp get()=application as ResourceApp
    private val main=Handler(Looper.getMainLooper())
    override fun onStartJob(params:JobParameters):Boolean {
        val run=Run(params);active=run
        app.repository.worker.execute {
            var retry=false
            try {
                if(run.stopped.get())return@execute
                val e=params.extras;val actor=e.getString("actor")?:error("missing actor")
                val id=e.getString("intent_id")?:error("missing id");val fp=e.getString("fingerprint")?:error("missing fp")
                val p=app.repository.client.get(actor,id)?:error("no durable intent")
                require(actor==BuildConfig.ACTOR&&p.fp==fp)
                if(p.result!=null) { app.resourceStore.audit("job_already_final",id) }
                else if(app.resourceStore.attempts(p)>=ResourceStore.MAX_ATTEMPTS) {
                    app.resourceStore.audit("budget_exhausted",id+": unknown is not a business rejection")
                } else if(!run.stopped.get()) {
                    val attempt=app.resourceStore.takeAttempt(p)
                    val transport=HttpsTransport(actor,if(Build.VERSION.SDK_INT>=28)params.network else null)
                    run.transport=transport
                    if(run.stopped.get())transport.cancel()
                    app.repository.client.phase(p,"sending")
                    app.resourceStore.audit("job_started",id+":attempt="+attempt)
                    try {
                        val q=transport.query(p,"self")
                        require(q.get("protocol")==Protocol.NAME&&q.get("actor")==actor&&q.get("intent_id")==id)
                        val reply=if(q.optString("status")=="unknown") {
                            require(q.keys().asSequence().toSet()==setOf("protocol","actor","intent_id","status","reason")&&q.get("reason")=="not_registered")
                            if(run.stopped.get())throw java.io.InterruptedIOException("job stopped before replay")
                            transport.reserve(p,"self")
                        } else q
                        app.repository.client.accept(p,reply)
                        app.resourceStore.outcome(p,"durable_"+reply.getString("status"))
                    } catch(ex:Exception) {
                        app.repository.client.phase(p,if(ex is HttpFailure&&ex.code==409)"protocol_error" else "unknown")
                        app.resourceStore.outcome(p,if(ex is HttpFailure)"HTTP "+ex.code else ex.javaClass.simpleName)
                        // Do not spin on credentials/protocol errors. I/O unknown may retry
                        // same id, subject to both system constraints and durable budget.
                        retry=ex is java.io.IOException&&ex !is HttpFailure&&attempt<ResourceStore.MAX_ATTEMPTS
                    }
                }
                app.exportResources()
            } catch(ex:Exception) {
                // Migration/storage failure: keep old files; no destructive recovery/send.
                java.io.File(filesDir,"job-error.txt").writeText(ex.javaClass.simpleName+": "+ex.message)
            } finally {
                main.post {
                    if(active===run&&!run.stopped.get()) { active=null;jobFinished(params,retry) }
                }
            }
        }
        return true // Work is asynchronous; onStartJob itself does no SQLite/network I/O.
    }
    override fun onStopJob(params:JobParameters):Boolean {
        val run=active
        if(run!=null&&run.params.jobId==params.jobId) {
            run.stopped.set(true);active=null
            val reason=if(Build.VERSION.SDK_INT>=31)params.stopReason.toString() else "API<31"
            app.repository.worker.execute {
                runCatching { app.resourceStore.audit("job_stopped","job="+params.jobId+":reason="+reason);app.exportResources() }
            }
            // Never block the main callback while a socket is being disconnected.
            Thread({ run.transport?.cancel() },"wwl175-cancel").apply { isDaemon=true;start() }
        }
        // A later bind rechecks persisted id/result/budget before any new send.
        // Cancellation cannot retract a transaction that already committed.
        return true
    }
}

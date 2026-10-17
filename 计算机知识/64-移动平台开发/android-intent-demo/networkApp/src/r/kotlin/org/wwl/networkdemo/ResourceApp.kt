package org.wwl.networkdemo

import android.app.Application
import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.os.PersistableBundle
import org.json.JSONObject
import org.wwl.intentdemo.Pending
import java.io.File

class ResourceApp:Application() {
    lateinit var repository:NetworkRepository
        private set
    lateinit var resourceStore:ResourceStore
        private set
    companion object { const val JOB_ID=17503 }
    override fun onCreate() { super.onCreate();repository=NetworkRepository(this);resourceStore=ResourceStore(this) }
    fun schedule(p:Pending) {
        require(p.actor==BuildConfig.ACTOR&&p.result==null) { "choose an unfinished persisted intent" }
        require(resourceStore.attempts(p)<ResourceStore.MAX_ATTEMPTS) { "budget exhausted; keep original identity" }
        val scheduler=getSystemService(JobScheduler::class.java)
        val old=scheduler.getPendingJob(JOB_ID)
        if(old!=null)require(old.extras.getString("actor")==p.actor&&old.extras.getString("intent_id")==p.id&&old.extras.getString("fingerprint")==p.fp) { "another intent occupies the one teaching job slot; do not erase it" }
        val extras=PersistableBundle().apply { putString("actor",p.actor);putString("intent_id",p.id);putString("fingerprint",p.fp) }
        val job=JobInfo.Builder(JOB_ID,ComponentName(this,IntentJobService::class.java))
            .setExtras(extras).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setRequiresCharging(true)
            .setPersisted(true).setBackoffCriteria(30_000,JobInfo.BACKOFF_POLICY_EXPONENTIAL).build()
        check(scheduler.schedule(job)==JobScheduler.RESULT_SUCCESS)
        resourceStore.audit("job_scheduled",p.id+":"+p.fp)
    }
    fun exportResources(extra:JSONObject=JSONObject()):JSONObject {
        val value=JSONObject().put("version_code",BuildConfig.VERSION_CODE).put("debuggable",BuildConfig.DEBUG)
            .put("resources",resourceStore.snapshot()).put("network",repository.exportState()).put("observation",extra)
        File(filesDir,"resource-state.json").writeText(value.toString(2));return value
    }
}

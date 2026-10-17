package org.wwl.networkdemo

import org.wwl.intentdemo.Protocol

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Process
import android.text.InputFilter
import android.text.InputType
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.util.UUID

/** No configChanges shortcut: normal Android recreation is part of this lesson. */
class ResourceActivity:Activity() {
    private val repo:NetworkRepository get()=(application as ResourceApp).repository
    lateinit var startInput:EditText
        private set
    lateinit var endInput:EditText
        private set
    lateinit var statusView:TextView
        private set
    private lateinit var detail:TextView
    private lateinit var resourceView:TextView
    private var resourceSummary="资源数据库尚未读取"
    private val extra=JSONObject()
    private var camera:android.hardware.camera2.CameraDevice?=null
    private var cameraToken=0L
    private var sensorRegistered=false
    private var sensorCount=0
    private val sensorManager by lazy { getSystemService(android.hardware.SensorManager::class.java) }
    private val sensorListener=object:android.hardware.SensorEventListener {
        override fun onAccuracyChanged(sensor:android.hardware.Sensor?,accuracy:Int) {}
        override fun onSensorChanged(event:android.hardware.SensorEvent) {
            if(!foreground||!sensorRegistered)return
            sensorCount++
            extra.put("sensor_samples",sensorCount).put("acceleration_m_s2",org.json.JSONArray(event.values.take(3)))
                .put("sensor_timestamp_ns",event.timestamp)
            // Keep the latest observation only; no sensor stream is uploaded.
            recordUi()
        }
    }
    private var generation=0L
    private var foreground=false
    private var savingIntent=false
    private val actions=mutableListOf<Button>()
    private var initializedDraft=false
    private var shownActor:String?=null
    private var shownId:String?=null
    private var lastState:JSONObject?=null
    private val instance=UUID.randomUUID().toString()
    private var pendingCommand:Intent?=null
    var lastDisplayedMessage:String="正在读取持久记录，尚未确认新预约。"
        private set
    private fun ticket():Long { generation++;return generation }
    private fun allowed(t:Long,key:String?=null):Boolean = foreground&&!isDestroyed&&t==generation&&
        (key==null||key=="$shownActor\u0000$shownId")

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        val body=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(24,16,24,24) }
        body.setOnApplyWindowInsetsListener { view,insets ->
            if(Build.VERSION.SDK_INT>=30) { val bars=insets.getInsets(WindowInsets.Type.systemBars());view.setPadding(24+bars.left,16+bars.top,24+bars.right,24+bars.bottom) }
            else { @Suppress("DEPRECATION") view.setPadding(24+insets.systemWindowInsetLeft,16+insets.systemWindowInsetTop,24+insets.systemWindowInsetRight,24+insets.systemWindowInsetBottom) }
            insets
        }
        fun text(value:String)=TextView(this).apply { text=value;textSize=18f;body.addView(this) }
        text("权限/后台/更新：版本${BuildConfig.VERSION_CODE}")
        text("公开测试凭据，真实本机TLS；本地排队不是容量承诺。两沙箱不等于两台实体设备。")
        text("开始分钟")
        startInput=EditText(this).apply { id=1001;contentDescription="开始分钟";inputType=InputType.TYPE_CLASS_NUMBER;filters=arrayOf(InputFilter.LengthFilter(32));setText(savedInstanceState?.getString("start_raw")?:"690");body.addView(this) }
        text("结束分钟")
        endInput=EditText(this).apply { id=1002;contentDescription="结束分钟";inputType=InputType.TYPE_CLASS_NUMBER;filters=arrayOf(InputFilter.LengthFilter(32));setText(savedInstanceState?.getString("end_raw")?:"720");body.addView(this) }
        initializedDraft=savedInstanceState!=null
        statusView=text(lastDisplayedMessage).apply { id=1003;accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE }
        fun button(label:String,action:()->Unit) { body.addView(Button(this).apply { text=label;setOnClickListener { action() };actions.add(this) }) }
        button("保存草稿（落盘）") { saveDraft() }
        button("新意图：仅本地排队") { queueDraft() }
        button("恢复：查询/同意图重放") { attempt("recover") }
        button("刷新本地记录") { refresh() }
        button("获取服务预约投影") { networkFetch() }
        button("可选：相机权限与设备打开（不拍摄）") { requestCamera() }
        button("可选：开始前台加速度观察") { startSensor() }
        button("停止传感器") { stopSensor() }
        button("为原意图安排受约束后台任务") { scheduleJob() }
        button("导出合成实验状态") { exportDiagnostic() }
        resourceView=text("资源状态尚未读取")
        detail=text("读取中")
        setContentView(ScrollView(this).apply { addView(body) })
        if(BuildConfig.DEBUG&&savedInstanceState==null&&intent.hasExtra("lab_command"))pendingCommand=Intent(intent)
        // Test-control extras are not a durable business command and must not repeat on recreation.
        setIntent(Intent(intent).apply { for(key in listOf("lab_command","start_raw","end_raw","intent_id"))removeExtra(key) })
        repo.audit("activity_create","pid=${Process.myPid()} instance=$instance")
    }
    override fun onResume() { super.onResume();foreground=true;repo.audit("activity_resume",instance);refresh() }
    override fun onPause() { foreground=false;generation++;cameraToken++;camera?.close();camera=null;stopSensor()
        repo.audit("activity_pause",instance);super.onPause() }
    override fun onStop() { repo.audit("activity_stop",instance);super.onStop() }
    override fun onDestroy() { foreground=false;generation++;repo.audit("activity_destroy",instance);super.onDestroy() }
    override fun onSaveInstanceState(outState:Bundle) {
        outState.putString("start_raw",startInput.text.toString());outState.putString("end_raw",endInput.text.toString())
        super.onSaveInstanceState(outState)
    }
    override fun onNewIntent(intent:Intent) { super.onNewIntent(intent)
        if(BuildConfig.DEBUG&&intent.hasExtra("lab_command")) { pendingCommand=Intent(intent);refresh() }
    }
    private fun message(value:String) { lastDisplayedMessage=value;statusView.text=value }
    fun refresh() {
        val t=ticket()
        repo.refresh loaded@{ state ->
            if(!allowed(t)) { repo.audit("ui_ignored","refresh:$instance:$t");return@loaded }
            render(state)
            pendingCommand?.let { cmd -> pendingCommand=null;runLabCommand(cmd) }
        }
    }
    private fun render(state:JSONObject) {
        lastState=state
        val c=state.getJSONObject("client")
        if(!initializedDraft) { val d=c.getJSONObject("draft");startInput.setText(d.getString("start_raw"));endInput.setText(d.getString("end_raw"));initializedDraft=true }
        val current=c.optJSONObject("current");shownActor=current?.getString("actor");shownId=current?.getString("intent_id")
        val phase=current?.getString("phase")
        message(when(phase) {
            "queued" -> "本地待发送：尚无服务承诺。"
            "sending" -> "正在等待：结果尚未确认；离开界面不等于撤销。"
            "unknown" -> "结果未知：保留原意图和输入，请查询/同意图重放。"
            "accepted" -> "已确认：HTTPS权威保存了原意图的预约结果。"
            "rejected" -> "已拒绝：${current.getJSONObject("result").getString("reason")}；输入保留。"
            "protocol_error" -> "协议错误：保留原意图，不猜测最终结果。"
            else -> "没有待显示意图；草稿不是已预约。"
        })
        val cached=state.optJSONObject("projection")?.optJSONObject("snapshot")?.optJSONArray("bookings")
        detail.text="actor=${BuildConfig.ACTOR} uid=${state.getInt("uid")}\nintent_id=${shownId?:"无"}\nfp=${current?.getString("fingerprint")?:"无"}\n本地状态=${phase?:"无"}\n缓存预约数=${cached?.length()?:"尚无投影"}\n测试凭据=${state.getString("credential_mode")}\n${state.getString("transport_hint")}\n当前结果=${current?.opt("result")?:"无"}"
        readResourceState()
        recordUi()
    }
    private fun recordUi() {
        showObservation()
        repo.recordUi(JSONObject().put("pid",Process.myPid()).put("activity_instance",instance).put("generation",generation)
            .put("foreground",foreground).put("actor",shownActor?:JSONObject.NULL).put("intent_id",shownId?:JSONObject.NULL)
            .put("start_raw",startInput.text.toString()).put("end_raw",endInput.text.toString()).put("message",lastDisplayedMessage)
            .put("resources_observation",JSONObject(extra.toString())).put("resource_message",if(::resourceView.isInitialized)resourceView.text.toString() else "").put("phase",lastState?.getJSONObject("client")?.optJSONObject("current")?.optString("phase")?:JSONObject.NULL))
    }
    private fun saving(value:Boolean) {
        savingIntent=value
        actions.forEach { it.isEnabled=!value };startInput.isEnabled=!value;endInput.isEnabled=!value
    }
    private fun rejectWhileSaving():Boolean {
        if(!savingIntent)return false
        message("新意图正在持久保存，请等待完成；没有发送旧意图。");recordUi();return true
    }
    fun queueDraft(id:String=UUID.randomUUID().toString()) {
        if(rejectWhileSaving())return
        val start=startInput.text.toString().toIntOrNull();val end=endInput.text.toString().toIntOrNull()
        if(start==null||end==null) { message("输入错误：需要整数分钟；原输入和已有意图保留。");recordUi();return }
        // Invalid intervals remain a service business rejection; no local success is invented.
        try { Protocol.text(id) } catch(_:IllegalArgumentException) { message("输入错误：意图id无效；原记录保留。");recordUi();return }
        val t=ticket();saving(true);message("正在持久保存新意图；保存失败则不发送。")
        repo.queue(start,end,id) { r ->
            saving(false)
            if(!allowed(t)) { repo.audit("ui_ignored","queue:$instance:$t");return@queue }
            r.onSuccess { render(it) }.onFailure { message("保存失败：未发送，保留输入及原记录。");recordUi() }
        }
    }
    fun saveDraft() {
        if(rejectWhileSaving())return
        val t=ticket();val s=startInput.text.toString();val e=endInput.text.toString()
        repo.saveDraft(s,e) { r -> if(allowed(t))r.onSuccess { render(it);message("草稿已落盘；未创建或发送预约。");recordUi() }.onFailure { message("保存草稿失败；输入保留。");recordUi() } }
    }
    fun attempt(mode:String) {
        if(rejectWhileSaving())return
        val actor=shownActor;val id=shownId
        if(actor==null||id==null) { message("请先将新意图持久排队；没有意图可发送。");recordUi();return }
        val t=ticket();val key="$actor\u0000$id";message("等待此原意图的结果；尚未新确认。")
        repo.attempt(actor,id,mode) reply@{ callbackKey,r ->
            if(!allowed(t,key)||callbackKey!=key) { repo.audit("ui_ignored","reply:$instance:$t:$id");return@reply }
            r.onSuccess { render(it) }.onFailure { message("协议/存储异常：原意图保留，需恢复查询。");recordUi() }
        }
    }
    fun networkFetch() {
        if(rejectWhileSaving())return
        val t=ticket()
        repo.fetch { r -> if(allowed(t))r.onSuccess { render(it) }.onFailure { message("缓存读取失败；不据此承诺容量。");recordUi() } }
    }
    fun credentials(mode:String) {
        if(rejectWhileSaving())return
        val t=ticket()
        repo.credential(mode) { r -> if(allowed(t))r.onSuccess { render(it) }.onFailure { message("测试凭据保存失败。");recordUi() } }
    }
    private fun showObservation() {
        if(!::resourceView.isInitialized)return
        val cameraState=when(val state=extra.optString("camera","not_requested")) {
            "not_requested" -> "尚未请求；预约不需要相机。"
            "permission_required" -> "需要系统相机授权；可拒绝，预约记录不变。"
            "denied_booking_unchanged","rationale_cancelled" -> "已拒绝或取消：不打开相机，预约不撤销；需要时可再查看权限说明/设置。"
            "granted_click_to_open" -> "已授权；再次点相机按钮才打开设备，随后立即关闭。"
            "opened_then_closed" -> "设备已打开并关闭；没有采集照片或上传。"
            "no_device" -> "此设备没有可用相机；仍可继续预约。"
            else -> "相机不可用（$state）；保留预约，请检查授权/设备占用。"
        }
        val acceleration=extra.optJSONArray("acceleration_m_s2")?.toString()?:"尚无样本"
        val sensorState=if(sensorRegistered)"仅前台观察中" else "未注册/已停止"
        resourceView.text=resourceSummary+"\n相机："+cameraState+
            "\n加速度："+sensorState+"，样本="+sensorCount+"，最新m/s²="+acceleration+
            "\n传感器值只作本机观察，不进入预约参数、不上传。"
    }
    private fun readResourceState() {
        val a=application as ResourceApp;val observation=JSONObject(extra.toString())
        a.repository.worker.execute {
            val r=runCatching { a.exportResources(observation) }
            runOnUiThread {
                if(!foreground||isDestroyed)return@runOnUiThread
                resourceSummary=r.fold({ "资源schema=${it.getJSONObject("resources").getInt("schema_version")} version=${BuildConfig.VERSION_CODE} debuggable=${BuildConfig.DEBUG}\n"+it.getJSONObject("resources").getJSONArray("work").toString() },
                    { "资源迁移/存储失败：原数据库保留，未清空；请安装修复版本。" })
                extra.put("resource_storage",if(r.isSuccess)"ready" else "unavailable")
                recordUi()
            }
        }
    }
    fun scheduleJob() {
        if(rejectWhileSaving())return
        val actor=shownActor;val id=shownId
        if(actor==null||id==null) { message("先持久排队；没有原意图可以调度。");return }
        val a=application as ResourceApp;val t=ticket()
        a.repository.worker.execute {
            val r=runCatching { val p=a.repository.client.get(actor,id)?:error("missing intent");a.schedule(p);a.exportResources() }
            runOnUiThread { if(allowed(t)) {
                message(if(r.isSuccess)"已登记系统任务：仍等网络/充电与调度，未承诺服务成功。" else "未登记任务：检查持久意图/预算/已有工作；原数据保留。")
                extra.put("schedule",if(r.isSuccess)"registered" else "refused");recordUi();readResourceState()
            } }
        }
    }
    fun requestCamera() {
        if(!foreground)return
        if(checkSelfPermission(android.Manifest.permission.CAMERA)!=android.content.pm.PackageManager.PERMISSION_GRANTED) {
            extra.put("camera","permission_required");recordUi()
            if(shouldShowRequestPermissionRationale(android.Manifest.permission.CAMERA)) {
                android.app.AlertDialog.Builder(this).setMessage("仅在前台打开相机设备后立即关闭；不拍照、不上传。拒绝不影响预约。")
                    .setNegativeButton("取消") { _,_ -> extra.put("camera","rationale_cancelled");recordUi() }
                    .setPositiveButton("继续请求") { _,_ -> requestPermissions(arrayOf(android.Manifest.permission.CAMERA),175) }.show()
            } else requestPermissions(arrayOf(android.Manifest.permission.CAMERA),175)
            return
        }
        try {
            val manager=getSystemService(android.hardware.camera2.CameraManager::class.java)
            val id=manager.cameraIdList.firstOrNull()
            if(id==null) { extra.put("camera","no_device");recordUi();return }
            val token=++cameraToken
            manager.openCamera(id,object:android.hardware.camera2.CameraDevice.StateCallback() {
            override fun onOpened(device:android.hardware.camera2.CameraDevice) {
                if(!foreground||token!=cameraToken) { device.close();return }
                camera=device;extra.put("camera","opened_then_closed").put("camera_id",id);device.close();camera=null;recordUi()
            }
            override fun onDisconnected(device:android.hardware.camera2.CameraDevice) { device.close();camera=null;if(foreground&&token==cameraToken) { extra.put("camera","disconnected");recordUi() } }
            override fun onError(device:android.hardware.camera2.CameraDevice,error:Int) { device.close();camera=null;if(foreground&&token==cameraToken) { extra.put("camera","device_error_"+error);recordUi() } }
        },android.os.Handler(mainLooper)) }
        catch(e:Exception) { extra.put("camera","unavailable_"+e.javaClass.simpleName);recordUi() }
    }
    override fun onRequestPermissionsResult(code:Int,permissions:Array<out String>,results:IntArray) {
        super.onRequestPermissionsResult(code,permissions,results)
        if(code==175) {
            val granted=checkSelfPermission(android.Manifest.permission.CAMERA)==android.content.pm.PackageManager.PERMISSION_GRANTED
            extra.put("camera",if(granted)"granted_click_to_open" else "denied_booking_unchanged");recordUi()
            // The system permission dialog may pause the activity; explicit next click opens.
        }
    }
    fun startSensor() {
        if(!foreground)return
        val sensor=sensorManager.getDefaultSensor(android.hardware.Sensor.TYPE_ACCELEROMETER)
        if(sensor==null) { extra.put("sensor","no_device");recordUi();return }
        if(sensorRegistered)return
        sensorRegistered=sensorManager.registerListener(sensorListener,sensor,200_000)
        extra.put("sensor",if(sensorRegistered)"registered_foreground" else "registration_failed");recordUi()
    }
    fun stopSensor() {
        sensorRegistered=false;sensorManager.unregisterListener(sensorListener)
        extra.put("sensor","unregistered").put("sensor_samples",sensorCount);recordUi()
    }
    fun exportDiagnostic() {
        val a=application as ResourceApp;val observation=JSONObject(extra.toString())
        a.repository.worker.execute {
            val result=runCatching {
                val state=a.exportResources(observation)
                val directory=getExternalFilesDir(null)?:error("no external app directory")
                java.io.File(directory,"synthetic-state.json").writeText(state.toString(2))
            }
            runOnUiThread { if(foreground&&!isDestroyed) { message(if(result.isSuccess)"已显式导出合成状态；只用于本实验。" else "导出失败；原数据库保留。");recordUi() } }
        }
    }
    private fun runLabCommand(cmd:Intent) {
        if(!BuildConfig.DEBUG)return
        when(cmd.getStringExtra("lab_command")) {
            "edit" -> { startInput.setText(cmd.getStringExtra("start_raw")?:"690");endInput.setText(cmd.getStringExtra("end_raw")?:"720");recordUi() }
            "queue" -> { startInput.setText(cmd.getStringExtra("start_raw")?:"690");endInput.setText(cmd.getStringExtra("end_raw")?:"720");queueDraft(cmd.getStringExtra("intent_id")?:UUID.randomUUID().toString()) }
            "save_draft" -> saveDraft()
            "recover" -> attempt("recover")
            "fetch" -> networkFetch()
            "schedule" -> scheduleJob()
            "camera" -> requestCamera()
            "sensor_start" -> startSensor()
            "sensor_stop" -> stopSensor()
            "export" -> exportDiagnostic()
            "snapshot" -> { readResourceState();recordUi() }
        }
    }
}

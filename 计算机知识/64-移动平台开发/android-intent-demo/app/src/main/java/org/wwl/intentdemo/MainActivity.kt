package org.wwl.intentdemo

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
class MainActivity:Activity() {
    private val repo:Repository get()=(application as IntentApp).repository
    lateinit var startInput:EditText
        private set
    lateinit var endInput:EditText
        private set
    lateinit var statusView:TextView
        private set
    private lateinit var detail:TextView
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
        text("本地假服务：意图恢复教学")
        text("仅合成D的一天预约，无HTTP/真实身份。离线/丢回复是故障开关，不是实际网络切换。")
        text("开始分钟")
        startInput=EditText(this).apply { id=1001;contentDescription="开始分钟";inputType=InputType.TYPE_CLASS_NUMBER;filters=arrayOf(InputFilter.LengthFilter(32));setText(savedInstanceState?.getString("start_raw")?:"690");body.addView(this) }
        text("结束分钟")
        endInput=EditText(this).apply { id=1002;contentDescription="结束分钟";inputType=InputType.TYPE_CLASS_NUMBER;filters=arrayOf(InputFilter.LengthFilter(32));setText(savedInstanceState?.getString("end_raw")?:"720");body.addView(this) }
        initializedDraft=savedInstanceState!=null
        statusView=text(lastDisplayedMessage).apply { id=1003;accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE }
        fun button(label:String,action:()->Unit) { body.addView(Button(this).apply { text=label;setOnClickListener { action() };actions.add(this) }) }
        button("保存草稿（落盘）") { saveDraft() }
        button("新意图：仅本地排队") { queueDraft() }
        button("发送：正常回复") { attempt("normal") }
        button("发送：提交后丢回复") { attempt("drop") }
        button("发送：提交前回滚") { attempt("before") }
        button("发送：延迟回复3秒") { attempt("delay") }
        button("恢复：查询/同意图重放") { attempt("recover") }
        button("刷新本地记录") { refresh() }
        detail=text("读取中")
        setContentView(ScrollView(this).apply { addView(body) })
        if(BuildConfig.DEBUG&&savedInstanceState==null&&intent.hasExtra("lab_command"))pendingCommand=Intent(intent)
        // Test-control extras are not a durable business command and must not repeat on recreation.
        setIntent(Intent(intent).apply { for(key in listOf("lab_command","start_raw","end_raw","intent_id"))removeExtra(key) })
        repo.audit("activity_create","pid=${Process.myPid()} instance=$instance")
    }
    override fun onResume() { super.onResume();foreground=true;repo.audit("activity_resume",instance);refresh() }
    override fun onPause() { foreground=false;generation++;repo.audit("activity_pause",instance);super.onPause() }
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
            "accepted" -> "已确认：假权威保存了原意图的预约结果。"
            "rejected" -> "已拒绝：${current.getJSONObject("result").getString("reason")}；输入保留。"
            "protocol_error" -> "协议错误：保留原意图，不猜测最终结果。"
            else -> "没有待显示意图；草稿不是已预约。"
        })
        detail.text="actor=D\nintent_id=${shownId?:"无"}\nfp=${current?.getString("fingerprint")?:"无"}\n本地状态=${phase?:"无"}\n假权威预约数=${state.getJSONObject("mock_authority").getJSONArray("bookings").length()}\n当前结果=${current?.opt("result")?:"无"}"
        recordUi()
    }
    private fun recordUi() {
        repo.recordUi(JSONObject().put("pid",Process.myPid()).put("activity_instance",instance).put("generation",generation)
            .put("foreground",foreground).put("actor",shownActor?:JSONObject.NULL).put("intent_id",shownId?:JSONObject.NULL)
            .put("start_raw",startInput.text.toString()).put("end_raw",endInput.text.toString()).put("message",lastDisplayedMessage)
            .put("phase",lastState?.getJSONObject("client")?.optJSONObject("current")?.optString("phase")?:JSONObject.NULL))
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
    private fun runLabCommand(cmd:Intent) {
        if(!BuildConfig.DEBUG)return
        when(cmd.getStringExtra("lab_command")) {
            "edit" -> { startInput.setText(cmd.getStringExtra("start_raw")?:"690");endInput.setText(cmd.getStringExtra("end_raw")?:"720");recordUi() }
            "queue" -> { startInput.setText(cmd.getStringExtra("start_raw")?:"690");endInput.setText(cmd.getStringExtra("end_raw")?:"720");queueDraft(cmd.getStringExtra("intent_id")?:UUID.randomUUID().toString()) }
            "save_draft" -> saveDraft()
            "normal","drop","before","delay","recover" -> attempt(cmd.getStringExtra("lab_command")!!)
            "snapshot" -> recordUi()
        }
    }
}

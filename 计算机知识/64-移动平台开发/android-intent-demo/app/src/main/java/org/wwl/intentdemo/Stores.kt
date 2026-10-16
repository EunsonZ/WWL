package org.wwl.intentdemo

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject

internal inline fun <T> SQLiteDatabase.atomic(block: () -> T): T {
    beginTransaction()
    try { val result=block();setTransactionSuccessful();return result } finally { endTransaction() }
}

private fun exactString(o:JSONObject,key:String):String { val v=o.get(key);require(v is String) { "string field required" };return v }
private fun exactLong(o:JSONObject,key:String):Long { val v=o.get(key);require(v is Int||v is Long) { "integer field required" };return (v as Number).toLong() }
private fun sameJson(a:Any?,b:Any?):Boolean = when {
    a is JSONObject && b is JSONObject -> a.keys().asSequence().toSet()==b.keys().asSequence().toSet() && a.keys().asSequence().all { sameJson(a.get(it),b.get(it)) }
    a is JSONArray && b is JSONArray -> a.length()==b.length() && (0 until a.length()).all { sameJson(a.get(it),b.get(it)) }
    (a is Int||a is Long)&&(b is Int||b is Long) -> (a as Number).toLong()==(b as Number).toLong()
    else -> a==b
}

data class Pending(val actor:String,val id:String,val start:Int,val end:Int,val fp:String,val phase:String,val result:String?) {
    val key:String get()="$actor\u0000$id"
    fun json():JSONObject=JSONObject().put("actor",actor).put("intent_id",id).put("start",start).put("end",end)
        .put("fingerprint",fp).put("phase",phase).put("result",if(result==null)JSONObject.NULL else JSONObject(result))
}

/** Android client layout v1; not the SE82 server's SQLite file layout. All access is on repository worker. */
class ClientStore(context:Context,name:String="client.db"):SQLiteOpenHelper(context,name,null,1) {
    override fun onCreate(db:SQLiteDatabase) {
        db.execSQL("CREATE TABLE intents(actor TEXT NOT NULL,intent_id TEXT NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,fp TEXT NOT NULL,phase TEXT NOT NULL,result TEXT,PRIMARY KEY(actor,intent_id))")
        db.execSQL("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execSQL("CREATE TABLE draft(singleton INTEGER PRIMARY KEY CHECK(singleton=1),start_raw TEXT NOT NULL,end_raw TEXT NOT NULL)")
        db.execSQL("INSERT INTO draft VALUES(1,'690','720')")
        db.execSQL("CREATE TABLE trace(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,detail TEXT NOT NULL)")
    }
    override fun onUpgrade(db:SQLiteDatabase,oldVersion:Int,newVersion:Int) { error("explicit client schema migration required; retained database") }
    fun audit(kind:String,detail:String) { writableDatabase.insertOrThrow("trace",null,ContentValues().apply { put("kind",kind);put("detail",detail) }) }
    fun draft():Pair<String,String> = readableDatabase.rawQuery("SELECT start_raw,end_raw FROM draft WHERE singleton=1",null).use { c -> check(c.moveToFirst());c.getString(0) to c.getString(1) }
    fun saveDraft(start:String,end:String) { require(start.length<=32&&end.length<=32);writableDatabase.execSQL("UPDATE draft SET start_raw=?,end_raw=? WHERE singleton=1",arrayOf(start,end)) }
    fun get(actor:String,id:String):Pending? = readableDatabase.rawQuery("SELECT actor,intent_id,start,end,fp,phase,result FROM intents WHERE actor=? AND intent_id=?",arrayOf(actor,id)).use { c ->
        if(!c.moveToFirst())null else Pending(c.getString(0),c.getString(1),c.getInt(2),c.getInt(3),c.getString(4),c.getString(5),if(c.isNull(6))null else c.getString(6))
    }
    fun current():Pending? {
        val actor=readableDatabase.rawQuery("SELECT value FROM meta WHERE key='actor'",null).use { if(it.moveToFirst())it.getString(0)else null } ?: return null
        val id=readableDatabase.rawQuery("SELECT value FROM meta WHERE key='id'",null).use { if(it.moveToFirst())it.getString(0)else null } ?: return null
        return get(actor,id)
    }
    fun queue(actor:String,id:String,start:Int,end:Int):Pending {
        Protocol.text(actor);Protocol.text(id);val fp=Protocol.fingerprint(actor,start,end)
        return writableDatabase.atomic {
            val old=get(actor,id)
            require(old==null||old.fp==fp) { "IntentConflict: existing parameters retained" }
            if(old==null)writableDatabase.execSQL("INSERT INTO intents VALUES(?,?,?,?,?,'queued',NULL)",arrayOf(actor,id,start,end,fp))
            saveDraft(start.toString(),end.toString())
            for((k,v) in listOf("actor" to actor,"id" to id))writableDatabase.execSQL("INSERT OR REPLACE INTO meta VALUES(?,?)",arrayOf(k,v))
            audit("persisted_before_send",id);get(actor,id)!!
        }
    }
    fun phase(p:Pending,value:String) {
        require(value in setOf("sending","unknown","protocol_error"))
        writableDatabase.atomic {
            // Once a terminal result is known, a retry attempt cannot downgrade it.
            writableDatabase.execSQL("UPDATE intents SET phase=? WHERE actor=? AND intent_id=? AND result IS NULL",arrayOf(value,p.actor,p.id))
            audit(value,p.id)
        }
    }
    fun accept(p:Pending,response:JSONObject) {
        require(exactString(response,"protocol")==Protocol.NAME && exactString(response,"actor")==p.actor && exactString(response,"intent_id")==p.id) { "unexpected response identity/version" }
        val state=exactString(response,"status")
        require(state in setOf("accepted","rejected") && exactString(response,"fingerprint")==p.fp && exactLong(response,"policy_version")==2L && exactLong(response,"writer_epoch")==2L) { "unexpected response contract" }
        if(state=="accepted") {
            val b=response.getJSONObject("booking")
            require(exactString(b,"owner")==p.actor&&exactLong(b,"start")==p.start.toLong()&&exactLong(b,"end")==p.end.toLong()&&exactLong(b,"policy_version")==2L&&exactLong(b,"id")>0&&exactString(response,"reason")=="created")
            Protocol.text(exactString(response,"event_id")) // Opaque identity; do not parse the current server's format.
        } else require(exactString(response,"reason") in setOf("invalid_interval","conflict_with_buffer"))
        writableDatabase.atomic {
            val saved=get(p.actor,p.id) ?: error("intent vanished")
            require(saved.fp==p.fp) { "intent changed" }
            if(saved.result!=null)require(sameJson(JSONObject(saved.result),response)) { "terminal result changed" }
            writableDatabase.execSQL("UPDATE intents SET phase=?,result=? WHERE actor=? AND intent_id=?",arrayOf(state,response.toString(),p.actor,p.id))
            audit("durable_result",p.id)
        }
    }
    fun recoverInflight() { writableDatabase.atomic {
        writableDatabase.execSQL("UPDATE intents SET phase='unknown' WHERE phase='sending' AND result IS NULL")
        audit("process_store_open","inflight is uncertain, never inferred rejected")
    } }
    fun snapshot():JSONObject {
        val all=JSONArray();readableDatabase.rawQuery("SELECT actor,intent_id FROM intents ORDER BY rowid",null).use { c -> while(c.moveToNext())all.put(get(c.getString(0),c.getString(1))!!.json()) }
        val log=JSONArray();readableDatabase.rawQuery("SELECT seq,kind,detail FROM trace ORDER BY seq",null).use { c -> while(c.moveToNext())log.put(JSONObject().put("seq",c.getLong(0)).put("kind",c.getString(1)).put("detail",c.getString(2))) }
        val d=draft();return JSONObject().put("current",current()?.json()?:JSONObject.NULL).put("draft",JSONObject().put("start_raw",d.first).put("end_raw",d.second)).put("intents",all).put("trace",log)
    }
}

/** Local function/JSON mock only. Both files share a device failure domain; there is no HTTP/authentication. */
class MockAuthority(context:Context,name:String="mock-authority.db"):SQLiteOpenHelper(context,name,null,1) {
    override fun onCreate(db:SQLiteDatabase) {
        db.execSQL("CREATE TABLE bookings(id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,policy_version INTEGER NOT NULL)")
        db.execSQL("CREATE TABLE intents(actor TEXT NOT NULL,intent_id TEXT NOT NULL,fp TEXT NOT NULL,outcome TEXT NOT NULL,PRIMARY KEY(actor,intent_id))")
        db.execSQL("CREATE TABLE outbox(event_id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
        for((owner,s,e) in listOf(Triple("A",540,600),Triple("B",600,630),Triple("C",650,680)))db.execSQL("INSERT INTO bookings(owner,start,end,policy_version) VALUES(?,?,?,1)",arrayOf(owner,s,e))
    }
    override fun onUpgrade(db:SQLiteDatabase,oldVersion:Int,newVersion:Int) { error("explicit mock schema migration required; retained database") }
    fun query(actor:String,id:String,expectedFp:String?=null):JSONObject {
        Protocol.text(actor);Protocol.text(id)
        return readableDatabase.rawQuery("SELECT fp,outcome FROM intents WHERE actor=? AND intent_id=?",arrayOf(actor,id)).use { c ->
            if(!c.moveToFirst())JSONObject().put("protocol",Protocol.NAME).put("actor",actor).put("intent_id",id).put("status","unknown").put("reason","not_registered")
            else { require(expectedFp==null||expectedFp==c.getString(0)) { "IntentConflict: query fingerprint" };JSONObject(c.getString(1)) }
        }
    }
    fun reserve(p:Pending,writerEpoch:Int=2,beforeCommit:Boolean=false):JSONObject = writableDatabase.atomic {
        val fp=Protocol.fingerprint(p.actor,p.start,p.end)
        require(fp==p.fp) { "IntentConflict: input fingerprint" }
        val saved=query(p.actor,p.id,fp)
        if(saved.getString("status")!="unknown")return@atomic saved
        require(writerEpoch==2) { "WriterFenced: no new decision" }
        val result=JSONObject().put("protocol",Protocol.NAME).put("actor",p.actor).put("intent_id",p.id).put("fingerprint",fp)
            .put("policy_version",2).put("writer_epoch",writerEpoch).put("status","rejected")
        var conflict=false
        readableDatabase.rawQuery("SELECT start,end FROM bookings",null).use { c -> while(c.moveToNext())if(!Protocol.compatible(p.start,p.end,c.getInt(0),c.getInt(1)))conflict=true }
        if(!Protocol.validInterval(p.start,p.end))result.put("reason","invalid_interval")
        else if(conflict)result.put("reason","conflict_with_buffer")
        else {
            val id=writableDatabase.insertOrThrow("bookings",null,ContentValues().apply { put("owner",p.actor);put("start",p.start);put("end",p.end);put("policy_version",2) })
            val eventId="booking:$id:created";val booking=JSONObject().put("id",id).put("owner",p.actor).put("start",p.start).put("end",p.end).put("policy_version",2)
            result.put("status","accepted").put("reason","created").put("booking",booking).put("event_id",eventId)
            val event=JSONObject().put("protocol",Protocol.NAME).put("event_id",eventId).put("kind","booking_created").put("booking",booking).put("actor",p.actor).put("intent_id",p.id).put("fingerprint",fp)
            writableDatabase.execSQL("INSERT INTO outbox VALUES(?,?)",arrayOf(eventId,event.toString()))
        }
        writableDatabase.execSQL("INSERT INTO intents VALUES(?,?,?,?)",arrayOf(p.actor,p.id,fp,result.toString()))
        if(beforeCommit)throw java.io.IOException("lab rollback before commit")
        result
    }
    fun snapshot():JSONObject {
        val rows=JSONArray();readableDatabase.rawQuery("SELECT id,owner,start,end,policy_version FROM bookings ORDER BY id",null).use { c -> while(c.moveToNext())rows.put(JSONObject().put("id",c.getLong(0)).put("owner",c.getString(1)).put("start",c.getInt(2)).put("end",c.getInt(3)).put("policy_version",c.getInt(4))) }
        val results=JSONArray();readableDatabase.rawQuery("SELECT outcome FROM intents ORDER BY rowid",null).use { c -> while(c.moveToNext())results.put(JSONObject(c.getString(0))) }
        val outbox=JSONArray();readableDatabase.rawQuery("SELECT payload FROM outbox ORDER BY rowid",null).use { c -> while(c.moveToNext())outbox.put(JSONObject(c.getString(0))) }
        return JSONObject().put("bookings",rows).put("intents",results).put("outbox",outbox)
    }
}

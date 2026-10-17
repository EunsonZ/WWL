package org.wwl.networkdemo

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import org.wwl.intentdemo.Pending

/** Resource accounting is separate from client.db's immutable business intentions. */
class ResourceStore(context:Context,name:String="resources.db",private val requestedVersion:Int=BuildConfig.COURSE_DB_VERSION,
    private val failMigration:Boolean=BuildConfig.COURSE_FAIL_MIGRATION):SQLiteOpenHelper(context,name,null,requestedVersion) {
    init { require(requestedVersion in 1..2) }
    companion object { const val MAX_ATTEMPTS=3 }
    override fun onCreate(db:SQLiteDatabase) {
        require(requestedVersion in 1..2)
        db.execSQL("CREATE TABLE work(actor TEXT NOT NULL,intent_id TEXT NOT NULL,fp TEXT NOT NULL,attempts INTEGER NOT NULL CHECK(attempts BETWEEN 0 AND 3),PRIMARY KEY(actor,intent_id))")
        db.execSQL("CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,detail TEXT NOT NULL)")
        if(requestedVersion==2)db.execSQL("ALTER TABLE work ADD COLUMN last_http TEXT NOT NULL DEFAULT 'none'")
    }
    override fun onUpgrade(db:SQLiteDatabase,old:Int,new:Int) {
        require(old==1&&new==2) { "explicit resource migration required; keep database" }
        db.execSQL("ALTER TABLE work ADD COLUMN last_http TEXT NOT NULL DEFAULT 'none'")
        if(failMigration)throw android.database.sqlite.SQLiteException("PUBLIC LAB: fail after ALTER; transaction must roll back")
        db.execSQL("INSERT INTO events(kind,detail) VALUES('migration','1->2 retained work/id/fp/attempts')")
    }
    override fun onDowngrade(db:SQLiteDatabase,old:Int,new:Int) { error("resource downgrade rejected; no destructive reset") }
    fun audit(kind:String,detail:String) { writableDatabase.execSQL("INSERT INTO events(kind,detail) VALUES(?,?)",arrayOf(kind,detail)) }
    fun attempts(p:Pending):Int = readableDatabase.rawQuery("SELECT fp,attempts FROM work WHERE actor=? AND intent_id=?",arrayOf(p.actor,p.id)).use {
        if(!it.moveToFirst())0 else { require(it.getString(0)==p.fp);it.getInt(1) }
    }
    fun takeAttempt(p:Pending):Int {
        val db=writableDatabase;db.beginTransaction()
        try {
            db.execSQL("INSERT OR IGNORE INTO work(actor,intent_id,fp,attempts) VALUES(?,?,?,0)",arrayOf(p.actor,p.id,p.fp))
            val old=attempts(p);require(old<MAX_ATTEMPTS) { "logical attempt budget exhausted; business remains unknown" }
            db.execSQL("UPDATE work SET attempts=? WHERE actor=? AND intent_id=?",arrayOf<Any>(old+1,p.actor,p.id))
            audit("budget_taken",p.id+":"+(old+1));db.setTransactionSuccessful();return old+1
        } finally { db.endTransaction() }
    }
    fun outcome(p:Pending,detail:String) {
        if(readableDatabase.version>=2)writableDatabase.execSQL("UPDATE work SET last_http=? WHERE actor=? AND intent_id=?",arrayOf(detail,p.actor,p.id))
        audit("job_outcome",p.id+":"+detail)
    }
    fun snapshot():JSONObject {
        val db=readableDatabase;val rows=JSONArray();val log=JSONArray()
        db.rawQuery("SELECT * FROM work ORDER BY actor,intent_id",null).use { c -> while(c.moveToNext()) {
            val v=JSONObject();for(i in 0 until c.columnCount)v.put(c.getColumnName(i),if(c.getColumnName(i)=="attempts")c.getInt(i) else c.getString(i));rows.put(v)
        } }
        db.rawQuery("SELECT seq,kind,detail FROM events ORDER BY seq",null).use { c -> while(c.moveToNext())log.put(JSONObject().put("seq",c.getInt(0)).put("kind",c.getString(1)).put("detail",c.getString(2))) }
        return JSONObject().put("schema_version",db.version).put("work",rows).put("events",log)
    }
}

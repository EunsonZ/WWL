package org.wwl.networkdemo

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.wwl.intentdemo.Pending
import org.wwl.intentdemo.Protocol
import java.util.UUID
import android.database.sqlite.SQLiteDatabase

@RunWith(AndroidJUnit4::class)
class ResourceInstrumentedTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private fun pending(start:Int=690,end:Int=720)=Pending("D","resource-budget-test",start,end,Protocol.fingerprint("D",start,end),"queued",null)
    private fun name()="resource-test-${UUID.randomUUID()}.db"
    @Test fun durableThreeBackgroundAttemptsNotThreeUserActions() {
        val name=name();val p=pending()
        try {
            ResourceStore(context,name,1,false).use { s ->
                assertEquals(1,s.takeAttempt(p));assertEquals(2,s.takeAttempt(p));assertEquals(3,s.takeAttempt(p))
                assertTrue(runCatching { s.takeAttempt(p) }.isFailure);assertEquals(3,s.attempts(p))
                assertTrue(runCatching { s.takeAttempt(pending(810,840)) }.isFailure);assertEquals(3,s.attempts(p))
            }
            ResourceStore(context,name,1,false).use { assertEquals(3,it.attempts(p)) }
        } finally { context.deleteDatabase(name) }
    }
    @Test fun failedAlterRollsBackThenSuccessfulMigrationRetainsIdentityAndBudget() {
        val name=name();val p=pending()
        try {
            ResourceStore(context,name,1,false).use { it.takeAttempt(p);it.takeAttempt(p) }
            ResourceStore(context,name,2,true).use { broken -> assertTrue(runCatching { broken.snapshot() }.isFailure) }
            SQLiteDatabase.openDatabase(context.getDatabasePath(name).path,null,SQLiteDatabase.OPEN_READONLY).use { db ->
                assertEquals(1,db.version)
                db.rawQuery("PRAGMA table_info(work)",null).use { c ->
                    val columns=mutableListOf<String>();while(c.moveToNext())columns.add(c.getString(1))
                    assertFalse(columns.contains("last_http"))
                }
                db.rawQuery("SELECT actor,intent_id,fp,attempts FROM work",null).use { c ->
                    assertTrue(c.moveToFirst());assertEquals("D",c.getString(0));assertEquals(p.id,c.getString(1));assertEquals(p.fp,c.getString(2));assertEquals(2,c.getInt(3));assertFalse(c.moveToNext())
                }
            }
            ResourceStore(context,name,2,false).use { good ->
                val state=good.snapshot();assertEquals(2,state.getInt("schema_version"))
                val row=state.getJSONArray("work").getJSONObject(0)
                assertEquals(p.fp,row.getString("fp"));assertEquals(2,row.getInt("attempts"));assertEquals("none",row.getString("last_http"))
            }
        } finally { context.deleteDatabase(name) }
    }
    @Test fun schemaDowngradeDoesNotEraseData() {
        val name=name();val p=pending()
        try {
            ResourceStore(context,name,2,false).use { it.takeAttempt(p) }
            ResourceStore(context,name,1,false).use { assertTrue(runCatching { it.snapshot() }.isFailure) }
            ResourceStore(context,name,2,false).use { assertEquals(1,it.attempts(p)) }
        } finally { context.deleteDatabase(name) }
    }
    @Test fun cancelledTransportDoesNotBeginNewConnection() {
        val transport=HttpsTransport("D");transport.cancel()
        val error=runCatching { transport.snapshot("self") }.exceptionOrNull()
        assertTrue(error is java.io.InterruptedIOException)
    }
}

package org.wwl.intentdemo

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class StoreInstrumentedTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private val clientName="test-client-${UUID.randomUUID()}.db"
    private val authorityName="test-authority-${UUID.randomUUID()}.db"
    private lateinit var client:ClientStore
    private lateinit var authority:MockAuthority
    @Before fun open() { client=ClientStore(context,clientName);authority=MockAuthority(context,authorityName) }
    @After fun close() { client.close();authority.close();context.deleteDatabase(clientName);context.deleteDatabase(authorityName) }
    private fun reopen() { client.close();authority.close();client=ClientStore(context,clientName);authority=MockAuthority(context,authorityName);client.recoverInflight() }
    @Test fun queuedBeforeAnySendSurvivesReopen() {
        val p=client.queue("D","persist-only",690,720);reopen();val q=client.current()!!
        assertEquals(p.id,q.id);assertEquals(p.fp,q.fp);assertEquals("queued",q.phase)
        assertEquals(3,authority.snapshot().getJSONArray("bookings").length())
        assertEquals("unknown",authority.query("D",p.id,p.fp).getString("status"))
    }
    @Test fun committedLostReplyReopensAndReplaysOriginalDecision() {
        val p=client.queue("D","lost-reply",690,720);client.phase(p,"sending")
        val original=authority.reserve(p) // transport deliberately does not deliver this result
        reopen();val q=client.current()!!;assertEquals("unknown",q.phase);assertEquals(p.id,q.id);assertEquals(p.fp,q.fp)
        val queried=authority.query(q.actor,q.id,q.fp);assertEquals(original.toString(),queried.toString())
        client.accept(q,queried);val replay=authority.reserve(q,writerEpoch=1)
        assertEquals(original.toString(),replay.toString());assertEquals(4L,replay.getJSONObject("booking").getLong("id"))
        assertEquals(4,authority.snapshot().getJSONArray("bookings").length());assertEquals(1,authority.snapshot().getJSONArray("outbox").length())
        assertEquals("accepted",client.current()!!.phase)
    }
    @Test fun rollbackIsUnknownNotFinalRejection() {
        val p=client.queue("D","before-commit",690,720)
        try { authority.reserve(p,beforeCommit=true);fail("expected fault") } catch(_:java.io.IOException) {}
        reopen();val query=authority.query(p.actor,p.id,p.fp)
        assertEquals("unknown",query.getString("status"));assertEquals("not_registered",query.getString("reason"));assertFalse(query.has("fingerprint"))
        assertEquals(3,authority.snapshot().getJSONArray("bookings").length())
        val accepted=authority.reserve(p);client.accept(p,accepted);assertEquals("accepted",client.current()!!.phase)
    }
    @Test fun bufferAndInvalidIntervalAreDurableBusinessRejections() {
        val p=client.queue("D","buffer",630,660);val r=authority.reserve(p);client.accept(p,r)
        assertEquals("conflict_with_buffer",r.getString("reason"));assertEquals("rejected",client.current()!!.phase)
        val invalid=client.queue("D","invalid",690,719);assertEquals("invalid_interval",authority.reserve(invalid).getString("reason"))
        assertEquals("690" to "719",client.draft());assertEquals(3,authority.snapshot().getJSONArray("bookings").length())
    }
    @Test fun sameKeyDifferentParametersCannotReplaceOriginal() {
        val p=client.queue("D","same-key",690,720);val saved=authority.reserve(p);client.accept(p,saved)
        try { client.queue("D",p.id,700,730);fail("expected conflict") } catch(_:IllegalArgumentException) {}
        val changed=p.copy(start=700,end=730,fp=Protocol.fingerprint("D",700,730))
        try { authority.reserve(changed);fail("expected authority conflict") } catch(_:IllegalArgumentException) {}
        assertEquals(p.fp,client.current()!!.fp);assertEquals(saved.toString(),authority.query("D",p.id,p.fp).toString())
        assertEquals("690" to "720",client.draft())
    }
    @Test fun malformedResultsAreNotDisplayedAsAccepted() {
        val p=client.queue("D","shape",690,720);val r=authority.reserve(p)
        for(bad in listOf(JSONObject(r.toString()).put("fingerprint","bad"),JSONObject(r.toString()).put("policy_version",2.0),JSONObject(r.toString()).put("intent_id","other"))) {
            try { client.accept(p,bad);fail("expected contract failure") } catch(_:IllegalArgumentException) {}
            assertEquals("queued",client.current()!!.phase)
        }
        client.accept(p,r)
        val reordered=JSONObject();for(k in r.keys().asSequence().toList().reversed())reordered.put(k,r.get(k))
        client.accept(p,reordered);assertEquals("accepted",client.current()!!.phase)
    }
}

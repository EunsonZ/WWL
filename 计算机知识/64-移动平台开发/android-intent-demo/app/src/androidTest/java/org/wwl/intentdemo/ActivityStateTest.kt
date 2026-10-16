package org.wwl.intentdemo

import android.content.pm.ActivityInfo
import android.content.res.Configuration
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class ActivityStateTest {
    private val repo get()=(InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as IntentApp).repository
    private fun waitFor(condition:()->Boolean) { val until=System.nanoTime()+8_000_000_000;while(System.nanoTime()<until){if(condition())return;Thread.sleep(40)};error("bounded state wait failed") }
    @Test fun immediateSendWhilePersistingDoesNotSendOldDisplayedIntent() {
        val oldId="old-${UUID.randomUUID()}";val newId="new-${UUID.randomUUID()}"
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { a -> a.startInput.setText("690");a.endInput.setText("720");a.queueDraft(oldId) }
            waitFor { repo.blocking { client.current()?.id==oldId } }
            // Let the old identity reach the actual screen, then make two same-main-thread calls.
            waitFor { var ok=false;scenario.onActivity { a -> ok=a.lastDisplayedMessage.contains("本地待发送") };ok }
            val before=repo.blocking { authority.snapshot().toString() }
            scenario.onActivity { a ->
                a.startInput.setText("810");a.endInput.setText("840");a.queueDraft(newId)
                assertFalse(a.startInput.isEnabled)
                a.attempt("normal") // Must not send oldId or invalidate the new queue's callback.
            }
            waitFor { repo.blocking { client.current()?.id==newId } }
            waitFor { var ok=false;scenario.onActivity { a -> ok=a.startInput.isEnabled&&a.lastDisplayedMessage.contains("本地待发送") };ok }
            assertEquals(before,repo.blocking { authority.snapshot().toString() })
            assertEquals("queued",repo.blocking { client.get("D",oldId)!!.phase })
            assertEquals("queued",repo.blocking { client.get("D",newId)!!.phase })
        }
    }
    @Test fun recreateAndRealOrientationKeepDurableIdentityAndBundleDraft() {
        val id="activity-${UUID.randomUUID()}"
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            waitFor { repo.blocking { client.current()!=null || client.draft().first=="690" } }
            scenario.onActivity { a -> a.startInput.setText("690");a.endInput.setText("720");a.queueDraft(id) }
            waitFor { repo.blocking { client.current()?.id==id } }
            val fp=repo.blocking { client.current()!!.fp }
            scenario.onActivity { a -> a.startInput.setText("bad") }
            scenario.recreate()
            scenario.onActivity { a -> assertEquals("bad",a.startInput.text.toString()) }
            assertEquals(id,repo.blocking { client.current()!!.id });assertEquals(fp,repo.blocking { client.current()!!.fp })
            var wanted=Configuration.ORIENTATION_LANDSCAPE
            scenario.onActivity { a ->
                wanted=if(a.resources.configuration.orientation==Configuration.ORIENTATION_LANDSCAPE)Configuration.ORIENTATION_PORTRAIT else Configuration.ORIENTATION_LANDSCAPE
                a.requestedOrientation=if(wanted==Configuration.ORIENTATION_LANDSCAPE)ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE else ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
            }
            waitFor { var ok=false;scenario.onActivity { a -> ok=a.resources.configuration.orientation==wanted };ok }
            scenario.onActivity { a -> assertEquals(wanted,a.resources.configuration.orientation);assertEquals("bad",a.startInput.text.toString()) }
            assertEquals(id,repo.blocking { client.current()!!.id });assertEquals(fp,repo.blocking { client.current()!!.fp })
            assertEquals("queued",repo.blocking { client.current()!!.phase })
        }
    }
}

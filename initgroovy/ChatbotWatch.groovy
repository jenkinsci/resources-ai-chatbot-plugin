import jenkins.model.Jenkins
import jenkins.util.Timer
import hudson.security.ACL
import java.nio.file.*
import java.util.concurrent.TimeUnit
import groovy.transform.Field

import static java.nio.file.StandardWatchEventKinds.*


@Field String PLUGIN_JPI = "resources-ai-chatbot-plugin.jpi"
@Field String PLUGIN_HPI = "resources-ai-chatbot-plugin.hpi"
@Field String UNINSTALL_JOB = "Chatbot-uninstall"

@Field File JENKINS_HOME = Jenkins.instance.rootDir
@Field File PLUGINS_DIR = new File(JENKINS_HOME, "plugins")

@Field File INSTALL_MARKER = new File(JENKINS_HOME, "chatbot-install.mkr")


@Field volatile boolean uninstallTriggered = false

println "[Chatbot Watcher] Jenkins starting. Scheduling watcher startup…"


Timer.get().schedule({

    println "[Chatbot Watcher] Startup delay elapsed. Starting plugin watcher."
    startWatcherSafely()

}, 9, TimeUnit.SECONDS)  

def startWatcherSafely() {

    if (!PLUGINS_DIR.exists()) {
        println "[Chatbot Watcher] Plugins directory not found. Aborting watcher."
        return
    }

    WatchService watchService = FileSystems.getDefault().newWatchService()

    PLUGINS_DIR.toPath().register(
        watchService,
        ENTRY_CREATE,
        ENTRY_MODIFY,
        ENTRY_DELETE
    )

    println "[Chatbot Watcher] Watching directory: ${PLUGINS_DIR.absolutePath}"

    while (true) {
        WatchKey key = watchService.take()
        println "[Chatbot Watcher] RAW EVENT RECEIVED"
        key.pollEvents().each { event ->

            def changed = event.context().toString()
            println "[Chatbot Watcher] Event: ${event.kind()} → ${changed}"

            if (changed.startsWith("resources-ai-chatbot")) {
            verifyPluginRemoval()
            }
        }
        key.reset()
    }
}

def verifyPluginRemoval() {

    if (uninstallTriggered) {
        return
    }

    sleep(1500)

    File jpi = new File(PLUGINS_DIR, PLUGIN_JPI)
    File hpi = new File(PLUGINS_DIR, PLUGIN_HPI)

    if (!jpi.exists() && !hpi.exists() && INSTALL_MARKER.exists()) {

        uninstallTriggered = true
        println "[Chatbot Watcher] Plugin confirmed removed."

        triggerUninstallJob()
        deleteMarkers()
    }
}

def triggerUninstallJob() {

    println "[Chatbot Watcher] Triggering uninstall job: ${UNINSTALL_JOB}"

    ACL.impersonate(ACL.SYSTEM)

    def job = Jenkins.instance.getItemByFullName(UNINSTALL_JOB)

    if (job == null) {
        println "[Chatbot Watcher] ERROR: Job not found: ${UNINSTALL_JOB}"
        return
    }

    job.scheduleBuild2(0)
}

def deleteMarkers() {

    if (INSTALL_MARKER.exists()) {
        INSTALL_MARKER.delete()
        println "[Chatbot Watcher] Install marker deleted."
    }

}

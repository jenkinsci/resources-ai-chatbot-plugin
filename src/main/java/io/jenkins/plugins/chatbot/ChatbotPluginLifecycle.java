package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.init.InitMilestone;
import hudson.init.Initializer;
import hudson.model.Job;
import hudson.model.Queue;
import hudson.model.Result;
import hudson.model.Run;
import hudson.model.TaskListener;
import hudson.model.listeners.RunListener;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Logger;
import jenkins.model.Jenkins;
import jenkins.util.Timer;

@Extension
public class ChatbotPluginLifecycle extends RunListener<Run<?, ?>> {

    private static final Logger LOGGER = Logger.getLogger(ChatbotPluginLifecycle.class.getName());

    private static final String INSTALL_JOB = "Chatbot-install";
    private static final String INSTALL_MARKER_FILE = "chatbot-install.mkr";

    private static final AtomicBoolean BOOTSTRAP_TRIGGERED = new AtomicBoolean(false);

    @Initializer(after = InitMilestone.PLUGINS_STARTED)
    public static void onJenkinsStartup() {
        LOGGER.info("Chatbot plugin detected. Scheduling bootstrap.");

        Timer.get().submit(() -> {
            try {
                bootstrap();
            } catch (Throwable t) {
                LOGGER.severe("Chatbot bootstrap failed: " + t.getMessage());
            }
        });
    }

    private static void bootstrap() {
        if (!BOOTSTRAP_TRIGGERED.compareAndSet(false, true)) {
            return;
        }

        Jenkins jenkins = Jenkins.get();
        File install_marker = new File(jenkins.getRootDir(), INSTALL_MARKER_FILE);

        if (!install_marker.exists()) {
            triggerJob(INSTALL_JOB);
            return;
        } else {
            LOGGER.info("Chatbot already running. No action needed.");
        }
    }

    private static void triggerJob(String jobName) {
        Job<?, ?> job = Jenkins.get().getItemByFullName(jobName, Job.class);
        if (job == null) {
            LOGGER.warning("Job not found: " + jobName);
            return;
        }

        LOGGER.info("Triggering job: " + jobName);
        Queue.Task task = (Queue.Task) job;
        Jenkins.get().getQueue().schedule(task, 0);
    }

    @Override
    public void onCompleted(Run<?, ?> run, TaskListener listener) {
        String jobName = run.getParent().getFullName();
        Result result = run.getResult();

        if (INSTALL_JOB.equals(jobName)) {
            handleInstallResult(result);
        }
    }

    private void handleInstallResult(Result result) {
        if (result == Result.SUCCESS) {
            LOGGER.info("Chatbot installed successfully.");
            createMarkerFile(INSTALL_MARKER_FILE);
        } else {
            LOGGER.warning("Chatbot installation failed.");
        }
    }

    private void createMarkerFile(String markerName) {
        try {
            File marker = new File(Jenkins.get().getRootDir(), markerName);

            if (marker.createNewFile()) {
                LOGGER.info(markerName + " file created.");
            } else {
                LOGGER.info(markerName + " file already exists.");
            }

        } catch (IOException e) {
            LOGGER.warning("Failed to create marker file: " + e.getMessage());
        }
    }
}

package io.jenkins.plugins.chatbot;

import hudson.Plugin;
import hudson.model.Executor;
import hudson.model.Job;
import hudson.model.Result;
import hudson.model.Run;
import java.util.logging.Logger;
import jenkins.model.Jenkins;

public class ChatbotPluginStop extends Plugin {

    private static final Logger LOGGER = Logger.getLogger(ChatbotPluginStop.class.getName());

    @Override
    public void stop() throws Exception {

        Job<?, ?> interruptJob = Jenkins.get().getItemByFullName("Chatbot-start", Job.class);

        try {
            if (interruptJob != null) {
                Run<?, ?> build = interruptJob.getLastBuild();
                if (build != null && build.isBuilding()) {
                    Executor executor = build.getExecutor();
                    if (executor != null) {
                        executor.interrupt(Result.ABORTED);
                        LOGGER.info("Interrupting running Chatbot-start job.");
                    }
                }
            }
        } catch (Exception e) {
            LOGGER.severe("Error while trying to interrupt Chatbot-start job: " + e.getMessage());
        }

        super.stop();
    }
}

package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.ExtensionList;
import hudson.init.InitMilestone;
import hudson.init.Initializer;
import hudson.init.Terminator;
import hudson.model.AdministrativeMonitor;
import hudson.model.Computer;
import java.io.File;
import java.io.IOException;
import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;
import jenkins.model.Jenkins;
import net.sf.json.JSONException;
import net.sf.json.JSONObject;

@Extension
public class BackendProcess extends AdministrativeMonitor {
    private static final Logger LOGGER = Logger.getLogger(BackendProcess.class.getName());
    private static final String[] PYTHON_PATHS = {"venv/bin/python", "venv/Scripts/python.exe"};
    private static final Duration STARTUP_TIMEOUT = Duration.ofMinutes(5);
    private static final HttpClient HTTP_CLIENT =
            HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();

    enum Health {
        RUNNING,
        NOT_RUNNING,
        OTHER_SERVICE
    }

    private Process process;
    private int generation;
    private String launchedUrl;
    private String launchedDirectory;
    private volatile String problem;

    public static BackendProcess get() {
        return ExtensionList.lookupSingleton(BackendProcess.class);
    }

    @Initializer(after = InitMilestone.JOB_CONFIG_ADAPTED)
    public static void startOnJenkinsStartup() {
        get().startInBackground();
    }

    @Terminator
    public static void stopOnJenkinsShutdown() {
        get().stop();
    }

    @Override
    public String getDisplayName() {
        return "Resources AI Chatbot backend";
    }

    @Override
    public boolean isActivated() {
        return problem != null;
    }

    public String getProblem() {
        return problem;
    }

    synchronized Process getProcess() {
        return process;
    }

    synchronized void onConfigurationChanged() {
        BackendConfiguration configuration = BackendConfiguration.get();
        if (!configuration.isAutoStartBackend()) {
            stop();
            problem = null;
            return;
        }
        if (launchedUrl != null
                && launchedUrl.equals(configuration.getBackendUrl())
                && Objects.equals(launchedDirectory, configuration.getBackendDirectory())) {
            return;
        }
        stop();
        launch();
    }

    synchronized void startInBackground() {
        if (launchedUrl == null && BackendConfiguration.get().isAutoStartBackend()) {
            launch();
        }
    }

    synchronized void stop() {
        generation++;
        launchedUrl = null;
        launchedDirectory = null;
        if (process != null && process.isAlive()) {
            LOGGER.info("Stopping the chatbot backend");
            process.destroy();
            try {
                if (!process.waitFor(10, TimeUnit.SECONDS)) {
                    process.destroyForcibly();
                }
            } catch (InterruptedException exception) {
                process.destroyForcibly();
                Thread.currentThread().interrupt();
            }
        }
        process = null;
    }

    private void launch() {
        BackendConfiguration configuration = BackendConfiguration.get();
        int launchGeneration = ++generation;
        launchedUrl = configuration.getBackendUrl();
        launchedDirectory = configuration.getBackendDirectory();
        problem = null;
        String url = launchedUrl;
        String directory = launchedDirectory;
        Computer.threadPoolForRemoting.execute(() -> start(launchGeneration, url, directory));
    }

    private synchronized boolean isCurrent(int launchGeneration) {
        return launchGeneration == generation;
    }

    private synchronized void fail(int launchGeneration, String message) {
        if (launchGeneration == generation) {
            launchedUrl = null;
            launchedDirectory = null;
            problem = message;
        }
    }

    private void start(int launchGeneration, String backendUrl, String backendDirectory) {
        Health health = checkHealth(backendUrl);
        if (health == Health.RUNNING) {
            LOGGER.info("The chatbot backend is already running at " + backendUrl);
            return;
        }
        if (health == Health.OTHER_SERVICE) {
            fail(
                    launchGeneration,
                    "Another service is using " + backendUrl + ", so the chatbot backend was not started.");
            return;
        }

        String error = validateDirectory(backendDirectory);
        if (error != null) {
            fail(launchGeneration, error);
            return;
        }

        File directory = new File(backendDirectory);
        File logFile = new File(Jenkins.get().getRootDir(), "logs/resources-ai-chatbot-backend.log");

        URI uri = URI.create(backendUrl);
        int port = uri.getPort() == -1 ? 80 : uri.getPort();
        ProcessBuilder builder = new ProcessBuilder(
                        findPython(directory).getPath(),
                        "-m",
                        "uvicorn",
                        "api.main:app",
                        "--host",
                        uri.getHost(),
                        "--port",
                        String.valueOf(port))
                .directory(directory)
                .redirectErrorStream(true)
                .redirectOutput(ProcessBuilder.Redirect.appendTo(logFile));
        builder.environment().put("PYTHONPATH", directory.getPath());

        Process started;
        synchronized (this) {
            if (!isCurrent(launchGeneration)) {
                return;
            }
            try {
                Files.createDirectories(logFile.getParentFile().toPath());
                started = builder.start();
            } catch (IOException exception) {
                LOGGER.log(Level.WARNING, "Failed to start the chatbot backend", exception);
                fail(launchGeneration, "Failed to start the chatbot backend: " + exception.getMessage());
                return;
            }
            process = started;
        }
        started.onExit()
                .thenAccept(exited -> fail(
                        launchGeneration,
                        "The chatbot backend stopped (exit code " + exited.exitValue() + "). See " + logFile
                                + " for details, then save the configuration to start it again."));
        LOGGER.info("Starting the chatbot backend from " + directory + ", logs are written to " + logFile);

        long deadline = System.nanoTime() + STARTUP_TIMEOUT.toNanos();
        while (System.nanoTime() < deadline) {
            if (!started.isAlive() || !isCurrent(launchGeneration)) {
                return;
            }
            if (checkHealth(backendUrl) == Health.RUNNING) {
                LOGGER.info("The chatbot backend is running at " + backendUrl);
                return;
            }
            try {
                Thread.sleep(2000);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                return;
            }
        }
        synchronized (this) {
            if (!isCurrent(launchGeneration)) {
                return;
            }
            stop();
            problem = "The chatbot backend did not start within " + STARTUP_TIMEOUT.toMinutes() + " minutes. See "
                    + logFile + " for details.";
        }
    }

    static Health checkHealth(String backendUrl) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(backendUrl + "/health"))
                .timeout(Duration.ofSeconds(3))
                .GET()
                .build();
        try {
            HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 200 && isChatbotHealthResponse(response.body())) {
                return Health.RUNNING;
            }
            return Health.OTHER_SERVICE;
        } catch (ConnectException | HttpConnectTimeoutException exception) {
            return Health.NOT_RUNNING;
        } catch (IOException exception) {
            return Health.OTHER_SERVICE;
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return Health.NOT_RUNNING;
        }
    }

    private static boolean isChatbotHealthResponse(String body) {
        try {
            JSONObject json = JSONObject.fromObject(body);
            return "healthy".equals(json.optString("status")) && json.has("llm_available");
        } catch (JSONException exception) {
            return false;
        }
    }

    private static File findPython(File directory) {
        for (String path : PYTHON_PATHS) {
            File python = new File(directory, path);
            if (python.isFile()) {
                return python;
            }
        }
        return null;
    }

    static String validateDirectory(String path) {
        if (path == null || path.isBlank()) {
            return "Backend directory is required when auto-start is enabled.";
        }
        File directory = new File(path.trim());
        if (!directory.isDirectory()) {
            return "Directory does not exist.";
        }
        if (!new File(directory, "api/main.py").isFile()) {
            return "This does not look like the chatbot-core directory (api/main.py not found).";
        }
        if (findPython(directory) == null) {
            return "Python virtual environment not found. Run make setup-backend first.";
        }
        return null;
    }
}

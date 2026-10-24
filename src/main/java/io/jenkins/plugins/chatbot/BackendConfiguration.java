package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.ExtensionList;
import hudson.model.Descriptor;
import hudson.util.FormValidation;
import java.net.URI;
import jenkins.model.GlobalConfiguration;
import jenkins.model.Jenkins;
import net.sf.json.JSONObject;
import org.kohsuke.stapler.QueryParameter;
import org.kohsuke.stapler.StaplerRequest2;
import org.kohsuke.stapler.verb.POST;

/**
 * Stores the URL of the FastAPI backend used by the chatbot and whether Jenkins starts it automatically.
 */
@Extension
public class BackendConfiguration extends GlobalConfiguration {
    private static final String DEFAULT_BACKEND_URL = "http://localhost:8000";

    private String backendUrl = DEFAULT_BACKEND_URL;
    private boolean autoStartBackend;
    private String backendDirectory;

    public BackendConfiguration() {
        load();
    }

    /**
     * Returns the Jenkins-wide backend configuration.
     *
     * @return the backend configuration singleton
     */
    public static BackendConfiguration get() {
        return ExtensionList.lookupSingleton(BackendConfiguration.class);
    }

    /**
     * Returns the configured FastAPI backend URL.
     *
     * @return the configured backend URL
     */
    public String getBackendUrl() {
        return backendUrl == null || backendUrl.isBlank() ? DEFAULT_BACKEND_URL : backendUrl;
    }

    public boolean isAutoStartBackend() {
        return autoStartBackend;
    }

    public String getBackendDirectory() {
        return backendDirectory;
    }

    @Override
    public boolean configure(StaplerRequest2 request, JSONObject json) throws Descriptor.FormException {
        String configuredUrl = json.optString("backendUrl", DEFAULT_BACKEND_URL);
        boolean autoStart = json.optBoolean("autoStartBackend");
        String directory = json.optString("backendDirectory", "").trim();

        String url;
        try {
            url = normalizeBackendUrl(configuredUrl);
        } catch (IllegalArgumentException exception) {
            throw new Descriptor.FormException(exception.getMessage(), "backendUrl");
        }

        if (autoStart) {
            String error = BackendProcess.validateDirectory(directory);
            if (error != null) {
                throw new Descriptor.FormException(error, "backendDirectory");
            }
            if (!isLocalUrlWithPort(url)) {
                throw new Descriptor.FormException(
                        "Auto-start only works with a local backend URL that includes a port, such as http://localhost:8000.",
                        "backendUrl");
            }
        }

        backendUrl = url;
        autoStartBackend = autoStart;
        backendDirectory = directory;
        save();
        BackendProcess.get().onConfigurationChanged();
        return true;
    }

    @POST
    public FormValidation doCheckBackendDirectory(@QueryParameter String value) {
        Jenkins.get().checkPermission(Jenkins.ADMINISTER);
        if (value == null || value.isBlank()) {
            return FormValidation.ok();
        }
        String error = BackendProcess.validateDirectory(value);
        return error == null ? FormValidation.ok() : FormValidation.error(error);
    }

    private static boolean isLocalUrlWithPort(String url) {
        URI uri = URI.create(url);
        return "http".equalsIgnoreCase(uri.getScheme())
                && ("localhost".equalsIgnoreCase(uri.getHost()) || "127.0.0.1".equals(uri.getHost()))
                && uri.getPort() != -1;
    }

    private static String normalizeBackendUrl(String value) {
        String candidate = value == null ? "" : value.trim();

        if (candidate.isEmpty()) {
            return DEFAULT_BACKEND_URL;
        }

        URI uri;
        try {
            uri = URI.create(candidate);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Backend URL must be a valid URL.", exception);
        }

        String scheme = uri.getScheme();
        if ((scheme == null || !(scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https")))
                || uri.getHost() == null
                || uri.getUserInfo() != null
                || uri.getQuery() != null
                || uri.getFragment() != null) {
            throw new IllegalArgumentException(
                    "Backend URL must use HTTP or HTTPS and contain a host without credentials, query parameters, or fragments.");
        }

        while (candidate.endsWith("/")) {
            candidate = candidate.substring(0, candidate.length() - 1);
        }

        return candidate;
    }
}

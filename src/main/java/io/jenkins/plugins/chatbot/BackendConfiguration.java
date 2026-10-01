package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.ExtensionList;
import hudson.model.Descriptor;
import java.net.URI;
import jenkins.model.GlobalConfiguration;
import net.sf.json.JSONObject;
import org.kohsuke.stapler.StaplerRequest2;

/**
 * Stores the URL of the FastAPI backend used by the chatbot.
 */
@Extension
public class BackendConfiguration extends GlobalConfiguration {
    private static final String DEFAULT_BACKEND_URL = "http://localhost:8000";

    private String backendUrl = DEFAULT_BACKEND_URL;

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

    @Override
    public boolean configure(StaplerRequest2 request, JSONObject json) throws Descriptor.FormException {
        String configuredUrl = json.optString("backendUrl", DEFAULT_BACKEND_URL);

        try {
            backendUrl = normalizeBackendUrl(configuredUrl);
        } catch (IllegalArgumentException exception) {
            throw new Descriptor.FormException(exception.getMessage(), "backendUrl");
        }

        save();
        return true;
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

import hudson.security.ACL
import jenkins.model.Jenkins

ACL.impersonate(ACL.SYSTEM)

def jobName = "Chatbot-start"
def job = Jenkins.instance.getItemByFullName(jobName)

if (job == null) {
    println "[Chatbot Watcher] ERROR: Job not found: ${jobName}"
    return
}

job.scheduleBuild2(0)

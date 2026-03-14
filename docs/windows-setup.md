# Windows/WSL2 Setup Guide for Local Development

This guide walks Windows users through setting up the Resources AI Chatbot Plugin
for local development using WSL2 (Windows Subsystem for Linux).

For official WSL2 documentation, refer to:
https://learn.microsoft.com/en-us/windows/wsl/install

## Prerequisites

- Windows 10 (build 19041+) or Windows 11
- At least 8GB RAM recommended

## Step 1 — Install WSL2

Open PowerShell as Administrator and run:
```powershell
wsl --install
```

This command installs WSL2 along with the default Ubuntu distribution.

**Restart your PC** after this completes.

After restart, Ubuntu will open automatically and ask you to create a username
and password. Complete that setup before proceeding.

To verify WSL2 is installed correctly, open PowerShell and run:
```powershell
wsl --list --verbose
```

Expected output:
NAME      STATE           VERSION

Ubuntu    Running         2


Make sure VERSION shows 2. If it shows 1, run:
```powershell
wsl --set-version Ubuntu 2
```

## Step 2 — Verify Ubuntu is Running

Before installing dependencies, confirm you are inside the Ubuntu terminal.
Open the Ubuntu app from the Windows Start menu. Your prompt should look like:
yourname@DESKTOP-XXXXX:~$

If you see `PS C:\Users\...` you are in PowerShell — close it and open Ubuntu instead.

## Step 3 — Install System Dependencies

Update the package list first:
```bash
sudo apt update
```

Install the required build tools:
```bash
sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev
```

Verify the installations:
```bash
# Verify cmake
cmake --version

# Verify gcc
gcc --version

# Verify Python 3.11
python3.11 --version
```

## Step 4 — Install Java 17

Install OpenJDK 17:
```bash
sudo apt install -y openjdk-17-jdk
```

Verify Java is installed correctly:
```bash
java -version
```

Expected output:
openjdk version "17.x.x" ...

## Step 5 — Install Maven 3.9+

The default Maven from apt is too old (3.6.x). Install 3.9+ manually.

First, set the version as a variable so it only needs to be updated here if the
version changes in the future:
```bash
MAVEN_VERSION=3.9.9
```

Download Maven:
```bash
wget https://downloads.apache.org/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz
```

Extract the archive:
```bash
tar -xzf apache-maven-${MAVEN_VERSION}-bin.tar.gz
```

Move it to /opt:
```bash
sudo mv apache-maven-${MAVEN_VERSION} /opt/maven
```

Add Maven to your PATH so it is available in every terminal session:
```bash
echo 'export PATH=/opt/maven/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

Verify Maven and Java versions:
```bash
mvn -version
```

Expected output:
Apache Maven 3.9.x (...)
Java version: 17.x.x

## Step 6 — Clone the Repository

Clone the repository inside WSL, not on the Windows filesystem:
```bash
cd ~
git clone https://github.com/jenkinsci/resources-ai-chatbot-plugin.git
cd resources-ai-chatbot-plugin
```

> ⚠️ Do NOT clone into `/mnt/c/...` (your Windows drive). Always work inside
> the WSL home directory (`~`) to avoid filesystem permission and performance issues.

## Step 7 — Run the Jenkins Plugin

Start Jenkins with the plugin loaded:
```bash
mvn hpi:run -Dchangelist=-SNAPSHOT -Dhost=0.0.0.0
```

- `-Dchangelist=-SNAPSHOT` resolves the version variable in pom.xml
- `-Dhost=0.0.0.0` binds Jenkins to all interfaces so it is reachable from Windows browser

Wait for this line before opening the browser:
Jenkins is fully up and running

## Step 8 — Open Jenkins in Browser

Open a **second Ubuntu terminal** (leave the first one running Jenkins), then run:
```bash
explorer.exe "http://localhost:8080/jenkins"
```

This opens your Windows browser pointing to the Jenkins instance running inside WSL.

## Common Errors and Fixes

### `Unknown packaging: hpi`
[ERROR] Unknown packaging: hpi @ io.jenkins.plugins:resources-ai-chatbot:${changelist}

**Fix:** Pass the changelist flag explicitly:
```bash
mvn hpi:run -Dchangelist=-SNAPSHOT -Dhost=0.0.0.0
```

### `version can neither be null, empty nor blank`

**Fix:** Do not use `-Dchangelist=` (empty value). Use `-Dchangelist=-SNAPSHOT` instead.

### `sudo is disabled on this machine`

You are in PowerShell, not WSL. Open the Ubuntu app from the Windows Start menu.

### `winget is not recognized`

Your Windows version may not have winget pre-installed. Use WSL2 instead
rather than installing dependencies natively on Windows.

### Browser shows `ERR_EMPTY_RESPONSE` on `localhost:8080`

Make sure you started Jenkins with `-Dhost=0.0.0.0` and open the browser
using `explorer.exe` from inside the WSL terminal, not from PowerShell.

## Notes

- Always run Maven and Git commands inside WSL, never in PowerShell
- Keep the Jenkins terminal running while you work — do not press Enter
  accidentally as this triggers a redeploy
- The repo must be cloned inside WSL (`~/`) not on the Windows filesystem (`/mnt/c/`)

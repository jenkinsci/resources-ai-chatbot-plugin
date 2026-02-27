# Windows/WSL2 Setup Guide for Local Development

This guide walks Windows users through setting up the Resources AI Chatbot Plugin
for local development using WSL2 (Windows Subsystem for Linux).

## Prerequisites

- Windows 10 (build 19041+) or Windows 11
- At least 8GB RAM recommended

## Step 1 — Install WSL2

Open PowerShell as Administrator and run:
```powershell
wsl --install
```

This installs WSL2 with Ubuntu automatically. **Restart your PC** after this completes.

After restart, Ubuntu will open and ask you to create a username and password.
Complete that setup before proceeding.

## Step 2 — Install System Dependencies

Inside your Ubuntu (WSL2) terminal, run:
```bash
sudo apt update && sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev
```

## Step 3 — Install Java 17
```bash
sudo apt install -y openjdk-17-jdk
java -version
```

## Step 4 — Install Maven 3.9+

The default Maven from apt is too old (3.6.x). Install 3.9+ manually:
```bash
wget https://downloads.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
tar -xzf apache-maven-3.9.9-bin.tar.gz
sudo mv apache-maven-3.9.9 /opt/maven
echo 'export PATH=/opt/maven/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
mvn -version
```

You should see Maven 3.9.x and Java 17.

## Step 5 — Clone the Repository

Clone inside WSL, not on the Windows filesystem:
```bash
cd ~
git clone https://github.com/jenkinsci/resources-ai-chatbot-plugin.git
cd resources-ai-chatbot-plugin
```

> ⚠️ Do NOT clone into `/mnt/c/...` (your Windows drive). Always work inside
> the WSL home directory (`~`) to avoid filesystem permission issues.

## Step 6 — Run the Jenkins Plugin
```bash
mvn hpi:run -Dchangelist=-SNAPSHOT -Dhost=0.0.0.0
```

## Step 7 — Open Jenkins in Browser

Open a **second Ubuntu terminal** (leave the first one running Jenkins), then run:
```bash
explorer.exe "http://localhost:8080/jenkins"
```

This opens your Windows browser pointing to the Jenkins instance running inside WSL.

## Common Errors and Fixes

### `Unknown packaging: hpi`

**Fix:** Pass the changelist flag explicitly:
```bash
mvn hpi:run -Dchangelist=-SNAPSHOT -Dhost=0.0.0.0
```

### `version can neither be null, empty nor blank`

**Fix:** Do not use `-Dchangelist=` (empty value). Use `-Dchangelist=-SNAPSHOT` instead.

### `sudo is disabled on this machine`

You are in PowerShell, not WSL. Open the Ubuntu app from the Start menu.

### `winget is not recognized`

Your Windows version may not have winget pre-installed. Use WSL2 instead rather than installing dependencies natively on Windows.

### Browser shows `ERR_EMPTY_RESPONSE` on `localhost:8080`

Make sure you started Jenkins with `-Dhost=0.0.0.0` and use `explorer.exe` from inside the WSL terminal to open the browser.

## Notes

- Always run Maven commands inside WSL, never in PowerShell
- Keep the Jenkins terminal running while you work — do not press Enter in it accidentally as this triggers a redeploy
- The repo must be cloned inside WSL (`~/`) not on the Windows filesystem (`/mnt/c/`)

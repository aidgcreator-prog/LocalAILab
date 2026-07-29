# LocalAiLab Assistant - Installer Guide

This guide explains how to package **LocalAiLab Assistant** into a single Windows setup file (`LocalAiLab_Setup.exe`) for laypeople.

---

## 🛠️ How to Build `LocalAiLab_Setup.exe`

### Step 1: Install Inno Setup (One-time developer setup)
1. Download **Inno Setup 6** (Free & Open Source) from:  
   👉 [https://jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
2. Run the Inno Setup installer using the default options.

### Step 2: Build the Installer
1. Double-click [BUILD_INSTALLER.bat](file:///g:/SmolAgent/BUILD_INSTALLER.bat) in the project directory.
2. The script will automatically locate `ISCC.exe` and compile [installer.iss](file:///g:/SmolAgent/installer.iss).
3. Upon completion, your output file will be saved to:
   ```text
   Output\LocalAiLab_Setup.exe
   ```

---

## 🚀 How the Installer Works for End Users (Laypeople)

When you send `LocalAiLab_Setup.exe` to a user:

1. **Double-Click Install**: The user double-clicks `LocalAiLab_Setup.exe`.
2. **Setup Wizard**: A clean Windows setup wizard guides them through installation.
3. **Automated Setup**: The installer extracts the files to `C:\Users\<User>\AppData\Roaming\LocalAiLab` and silently runs `SETUP.bat -NonInteractive` in the background to set up Python and install PyTorch/dependencies optimized for their specific hardware (Nvidia GPU, AMD, or CPU-only).
4. **Desktop Icon**: The installer creates a **LocalAiLab Assistant** shortcut on their Desktop and Start Menu.
5. **Launch**: Double-clicking the Desktop icon runs [RUN.bat](file:///g:/SmolAgent/RUN.bat) and opens the application in their default web browser.

---

## 📁 File Structure Overview

* **[installer.iss](file:///g:/SmolAgent/installer.iss)**: Inno Setup compiler configuration file.
* **[BUILD_INSTALLER.bat](file:///g:/SmolAgent/BUILD_INSTALLER.bat)**: Automated build script for compiling `LocalAiLab_Setup.exe`.
* **`Output\LocalAiLab_Setup.exe`**: The final executable installer file to distribute to users.

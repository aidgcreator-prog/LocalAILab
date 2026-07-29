; =====================================================================
; Inno Setup Script for LocalAiLab Assistant
; =====================================================================
; This script packages LocalAiLab Assistant into a single Windows Setup
; wizard (LocalAiLab_Setup.exe). When executed by an end user, it extracts
; the source files, runs SETUP.bat silently to create the Python venv &
; install PyTorch/dependencies, and creates Desktop/Start Menu shortcuts.
; =====================================================================

#define MyAppName "LocalAiLab Assistant"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LocalAiLab"
#define MyAppExeName "RUN.bat"
#define MyOutputBaseFilename "LocalAiLab_Setup"

[Setup]
AppId={{8F92E341-B8D2-4C10-9E11-54A62D719F8C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\LocalAiLab
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename={#MyOutputBaseFilename}
OutputDir=Output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all project files into the installation directory
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.venv\*,chroma_db\*,__pycache__\*,Output\*,*.log"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"; Tasks: desktopicon

[Run]
; Run SETUP.bat silently after extraction to create venv & install hardware-optimized dependencies
Filename: "{app}\SETUP.bat"; Parameters: "-NonInteractive"; StatusMsg: "Building Python environment & hardware-optimized AI dependencies... (This may take a few minutes)"; Flags: runhidden waituntilterminated

[UninstallDelete]
; Clean up runtime-generated virtual environment and caches on uninstall
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\chroma_db"

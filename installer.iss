; =====================================================================
; Inno Setup Script for LocalAiLab Assistant
; =====================================================================
; This script packages LocalAiLab Assistant into a single Windows Setup
; wizard (LocalAiLab_Setup_v0.0.4.exe). When executed by an end user, it extracts
; the source files, runs SETUP.bat silently to create the Python venv &
; install PyTorch/dependencies, and creates Desktop/Start Menu shortcuts.
;
; Only runtime files are packaged. Developer-only folders (.venv, .git,
; .planning, graphify-out, Output, __pycache__, chroma_db, data_analysis,
; visual_index) and build scripts (BUILD_INSTALLER.bat, installer.iss,
; install.ps1, install.bat, INSTALLER_GUIDE.md, RELEASE_NOTES_*) are NOT
; included — they are unrelated to the end-user runtime and only bloat
; the installer.
; =====================================================================

#define MyAppName "LocalAiLab Assistant"
#define MyAppVersion "0.0.3 beta"
#define MyAppPublisher "LocalAiLab"
#define MyAppExeName "RUN.bat"
#define MyOutputBaseFilename "LocalAiLab_Setup_v0.0.3"

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
DisableDirPage=no
UsePreviousAppDir=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ── Application code (root-level .py modules & model registries) ──
Source: "*.py";                       DestDir: "{app}"; Flags: ignoreversion
Source: "*.csv";                      DestDir: "{app}"; Flags: ignoreversion
; ── Setup & launch scripts ─────────────────────────────────────────
Source: "requirements.txt";           DestDir: "{app}"; Flags: ignoreversion
Source: "SETUP.bat";                  DestDir: "{app}"; Flags: ignoreversion
Source: "SETUP.ps1";                  DestDir: "{app}"; Flags: ignoreversion
Source: "RUN.bat";                    DestDir: "{app}"; Flags: ignoreversion
Source: "RUN.ps1";                    DestDir: "{app}"; Flags: ignoreversion
; ── Docs & licensing ───────────────────────────────────────────────
Source: "README.md";                  DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE";                    DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_LICENSES.md";    DestDir: "{app}"; Flags: ignoreversion
; ── Branding (loaded by branding.py at runtime) ────────────────────
Source: "image\logo.jpg";             DestDir: "{app}\image"; Flags: ignoreversion
; ── Bundled Poppler (PDF rendering for pdf2image). Bundling it means
;    the end user never has to download it at install time. ────────
Source: "poppler\*";                  DestDir: "{app}\poppler"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"; Tasks: desktopicon

[UninstallDelete]
; Clean up runtime-generated virtual environment, status files, caches,
; and empty bundled subfolders on uninstall.
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\chroma_db"
Type: files; Name: "{app}\install_progress.txt"
Type: files; Name: "{app}\install_status.txt"
Type: filesandordirs; Name: "{app}\data_analysis"
Type: filesandordirs; Name: "{app}\visual_index"
Type: filesandordirs; Name: "{app}\user"
Type: files; Name: "{app}\user_config.json"
Type: files; Name: "{app}\*.log"
Type: dirifempty; Name: "{app}\image"
Type: dirifempty; Name: "{app}\poppler"

[Code]
var
  g_hProcess: THandle;
  g_ProcessID: Integer;
  g_IsRunningSetup: Boolean;
  g_UserCancelled: Boolean;

function OpenProcess(dwDesiredAccess: DWORD; bInheritHandle: Boolean; dwProcessId: DWORD): THandle;
external 'OpenProcess@kernel32.dll stdcall';

function GetExitCodeProcess(hProcess: THandle; out lpExitCode: DWORD): Boolean;
external 'GetExitCodeProcess@kernel32.dll stdcall';

function TerminateProcess(hProcess: THandle; uExitCode: UINT): Boolean;
external 'TerminateProcess@kernel32.dll stdcall';

function CloseHandle(hObject: THandle): Boolean;
external 'CloseHandle@kernel32.dll stdcall';

const
  PROCESS_QUERY_INFORMATION = $0400;
  PROCESS_TERMINATE         = $0001;
  STILL_ACTIVE              = 259;
  POLL_INTERVAL_MS          = 150;
  SETUP_TIMEOUT_MS          = 7200000; { 2-hour safety cap so a hung process can never block the wizard forever }

procedure KillSetupProcessTree;
var
  KillResult: Integer;
begin
  if g_hProcess <> 0 then
  begin
    TerminateProcess(g_hProcess, 1);
    CloseHandle(g_hProcess);
    g_hProcess := 0;
  end;
  if g_ProcessID <> 0 then
  begin
    Exec(ExpandConstant('{cmd}'), '/c taskkill /F /T /PID ' + IntToStr(g_ProcessID), '', SW_HIDE, ewWaitUntilTerminated, KillResult);
    g_ProcessID := 0;
  end;
end;

procedure CancelButtonClicked(var Cancel, Confirm: Boolean);
begin
  if g_IsRunningSetup then
  begin
    if SuppressibleMsgBox('Are you sure you want to cancel the installation?', mbConfirmation, MB_YESNO, IDNO) = IDYES then
    begin
      g_UserCancelled := True;
      KillSetupProcessTree;
      Cancel := True;
      Confirm := False;
    end
    else
    begin
      Cancel := False;
      Confirm := False;
    end;
  end;
end;

procedure ParseProgressLine(const Line: String; var Pct: Integer; var Title, Detail: String);
var
  P1, P2: Integer;
  Rest: String;
begin
  P1 := Pos('|', Line);
  if P1 > 0 then
  begin
    Pct := StrToIntDef(Copy(Line, 1, P1 - 1), Pct);
    Rest := Copy(Line, P1 + 1, Length(Line) - P1);
    P2 := Pos('|', Rest);
    if P2 > 0 then
    begin
      Title := Copy(Rest, 1, P2 - 1);
      Detail := Copy(Rest, P2 + 1, Length(Rest) - P2);
    end
    else
    begin
      Title := Rest;
      Detail := '';
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDir: String;
  BatCmd: String;
  BatParams: String;
  ExitCode: DWORD;
  ProgressFile: String;
  StatusFile: String;
  Lines: TArrayOfString;
  Pct: Integer;
  Title: String;
  Detail: String;
  Success: Boolean;
  StatusLines: TArrayOfString;
  PollCount: Integer;
  TimedOut: Boolean;
  ProcessDone: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir := ExpandConstant('{app}');
    ProgressFile := AppDir + '\install_progress.txt';
    StatusFile := AppDir + '\install_status.txt';

    DeleteFile(ProgressFile);
    DeleteFile(StatusFile);

    WizardForm.StatusLabel.Caption := 'Building Python environment & hardware-optimized AI dependencies...';
    WizardForm.FilenameLabel.Caption := 'Initializing setup process...';
    WizardForm.ProgressGauge.Position := 0;

    WizardForm.CancelButton.Visible := True;
    WizardForm.CancelButton.Enabled := True;

    g_IsRunningSetup := True;
    g_UserCancelled := False;
    g_hProcess := 0;
    g_ProcessID := 0;

    BatCmd := ExpandConstant('{cmd}');
    BatParams := '/c ""' + AppDir + '\SETUP.bat" -NonInteractive"';

    if Exec(BatCmd, BatParams, AppDir, SW_HIDE, ewNoWait, g_ProcessID) then
    begin
      g_hProcess := OpenProcess(PROCESS_QUERY_INFORMATION or PROCESS_TERMINATE, False, g_ProcessID);
      Pct := 0;
      ExitCode := STILL_ACTIVE;
      ProcessDone := False;
      TimedOut := False;
      PollCount := 0;

      { SETUP.ps1 is guaranteed to write install_status.txt ('0' = success,
        '1' = failure) on EVERY exit path, so the status file is the
        authoritative completion signal. The process handle is only a
        fallback; if OpenProcess failed (g_hProcess = 0) we keep waiting on
        the status file instead of aborting, which used to let a
        still-running install be misreported as an instant failure and
        killed. }
      repeat
        Sleep(POLL_INTERVAL_MS);
        Inc(PollCount);
        WizardForm.CancelButton.Enabled := True;
        WizardForm.StatusLabel.Update;
        WizardForm.FilenameLabel.Update;
        WizardForm.ProgressGauge.Update;
        WizardForm.Update;

        if g_UserCancelled then Break;

        if FileExists(ProgressFile) then
        begin
          if LoadStringsFromFile(ProgressFile, Lines) and (GetArrayLength(Lines) > 0) then
          begin
            ParseProgressLine(Lines[0], Pct, Title, Detail);
            if Title <> '' then WizardForm.StatusLabel.Caption := Title;
            if Detail <> '' then WizardForm.FilenameLabel.Caption := Detail;
            if (Pct >= 0) and (Pct <= 100) then WizardForm.ProgressGauge.Position := Pct;
          end;
        end;

        if not ProcessDone then
        begin
          if (g_hProcess <> 0) and GetExitCodeProcess(g_hProcess, ExitCode) then
            ProcessDone := (ExitCode <> STILL_ACTIVE);
        end;

        TimedOut := (PollCount * POLL_INTERVAL_MS) >= SETUP_TIMEOUT_MS;
      until FileExists(StatusFile) or ProcessDone or g_UserCancelled or TimedOut;

      Success := False;
      if FileExists(StatusFile) then
      begin
        if LoadStringsFromFile(StatusFile, StatusLines) and (GetArrayLength(StatusLines) > 0) then
        begin
          if StatusLines[0] = '0' then
            Success := True;
        end;
      end;

      if g_UserCancelled then
      begin
        KillSetupProcessTree;
        WizardForm.StatusLabel.Caption := 'Installation cancelled by user.';
        WizardForm.FilenameLabel.Caption := '';
      end
      else if TimedOut then
      begin
        KillSetupProcessTree;
        WizardForm.StatusLabel.Caption := 'Environment setup timed out.';
        WizardForm.FilenameLabel.Caption := '';
        MsgBox('The environment setup script did not finish within the time limit. This is usually caused by a slow or interrupted internet connection during the large PyTorch/AI dependency download.' + #13#10 + #13#10 + 'To retry, open the folder "' + AppDir + '" and double-click SETUP.bat.', mbError, MB_OK);
      end
      else if not Success then
      begin
        KillSetupProcessTree;
        WizardForm.StatusLabel.Caption := 'Environment setup FAILED! Check the command window.';
        WizardForm.FilenameLabel.Caption := '';
        MsgBox('The environment setup script encountered an error while installing dependencies (e.g. PyTorch, Gradio, etc).' + #13#10 + #13#10 + 'To see the exact error, open the folder "' + AppDir + '" and double-click SETUP.bat manually.', mbError, MB_OK);
      end
      else
      begin
        if g_hProcess <> 0 then CloseHandle(g_hProcess);
        g_hProcess := 0;
        WizardForm.ProgressGauge.Position := 100;
        WizardForm.StatusLabel.Caption := 'Environment setup completed successfully.';
        WizardForm.FilenameLabel.Caption := '';
      end;

      g_IsRunningSetup := False;

      DeleteFile(ProgressFile);
      DeleteFile(StatusFile);
    end
    else
    begin
      g_IsRunningSetup := False;
      SuppressibleMsgBox('Failed to launch SETUP.bat automatically. Please run SETUP.bat manually inside ' + AppDir, mbError, MB_OK, IDOK);
    end;
  end;
end;

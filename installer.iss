; =====================================================================
; Inno Setup Script for LocalAiLab Assistant
; =====================================================================
; This script packages LocalAiLab Assistant into a single Windows Setup
; wizard (LocalAiLab_Setup_v0.0.3.exe). When executed by an end user, it extracts
; the source files, runs SETUP.bat silently to create the Python venv &
; install PyTorch/dependencies, and creates Desktop/Start Menu shortcuts.
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
; Copy all project files into the installation directory
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.venv\*,chroma_db\*,__pycache__\*,Output\*,*.log,user_config.json"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"; Tasks: desktopicon

[UninstallDelete]
; Clean up runtime-generated virtual environment, status files, and caches on uninstall
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\chroma_db"
Type: files; Name: "{app}\install_progress.txt"
Type: files; Name: "{app}\install_status.txt"

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

      repeat
        Sleep(150);
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

        if g_hProcess <> 0 then
          GetExitCodeProcess(g_hProcess, ExitCode)
        else
          ExitCode := 0;
      until (ExitCode <> STILL_ACTIVE) or FileExists(StatusFile) or g_UserCancelled;

      if g_UserCancelled then
      begin
        KillSetupProcessTree;
        WizardForm.StatusLabel.Caption := 'Installation cancelled by user.';
        WizardForm.FilenameLabel.Caption := '';
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

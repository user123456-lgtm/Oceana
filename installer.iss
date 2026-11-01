#define MyAppName "OCEANA Executor"
#define MyAppVersion "1.0.1"
#define MyAppExeName "OCEANA.exe"
[Setup]
AppId={{A8D7E7B3-2D41-4D20-9A10-0CE0A0000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\OCEANA
DefaultGroupName=OCEANA Executor
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=OCEANA-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
[Files]
Source: "dist\OCEANA.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autodesktop}\OCEANA Executor"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\OCEANA Executor"; Filename: "{app}\{#MyAppExeName}"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch OCEANA Executor"; Flags: nowait postinstall skipifsilent

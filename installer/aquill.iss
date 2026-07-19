#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\app\dist\windows\Aquill"
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif

[Setup]
AppId={{3EC49244-B102-400E-9798-1FC35F1EA929}
AppName=Aquill
AppVersion={#AppVersion}
AppVerName=Aquill {#AppVersion}
AppPublisher=Two Hands Network
AppCopyright=PolyForm Noncommercial License 1.0.0
AppPublisherURL=https://github.com/Martin123132/aquill
AppSupportURL=https://github.com/Martin123132/aquill/issues
AppUpdatesURL=https://github.com/Martin123132/aquill/releases
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=Two Hands Network
VersionInfoDescription=Aquill local transcription workbench installer
VersionInfoProductName=Aquill
DefaultDirName=D:\Apps\Aquill
DefaultGroupName=Aquill
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=Aquill-Setup-{#AppVersion}-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Aquill.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Aquill"; Filename: "{app}\Aquill.exe"
Name: "{autodesktop}\Aquill"; Filename: "{app}\Aquill.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Aquill.exe"; Description: "Launch Aquill"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := DirExists('D:\');
  if not Result then
    MsgBox('Aquill requires a D: drive for its application and local data.', mbError, MB_OK);
end;

[Setup]
; Унікальний ID проекту (не змінюйте його в майбутніх версіях)
AppId={{H264-PRO-TRIMMER-9911-2024}}
AppName=H264 Pro Trimmer
AppVersion={#AppVersion}
DefaultDirName={autopf}\H264ProTrimmer
DefaultGroupName=H264 Pro Trimmer
UninstallDisplayIcon={app}\H264ProTrimmer.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
; Беремо ВСІ файли з папки, яку створив PyInstaller
Source: "dist\H264ProTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\H264 Pro Trimmer"; Filename: "{app}\H264ProTrimmer.exe"
Name: "{autodesktop}\H264 Pro Trimmer"; Filename: "{app}\H264ProTrimmer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\H264ProTrimmer.exe"; Description: "{cm:LaunchProgram,H264 Pro Trimmer}"; Flags: nowait postinstall skipifsilent
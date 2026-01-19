#ifndef AppVersion
  #define AppVersion "v1.0.0"
#endif

[Setup]
AppId={{H264-PRO-TRIMMER-9911-2024}}
AppName=H264 Pro Trimmer
AppVersion={#AppVersion}
OutputBaseFilename=H264Trimmer_Setup_{#AppVersion}
DefaultDirName={autopf}\H264ProTrimmer
DefaultGroupName=H264 Pro Trimmer
UninstallDisplayIcon={app}\H264ProTrimmer.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Метадані (Виправлено назви директив)
VersionInfoCompany=H264 Pro Project
VersionInfoDescription=Lossless Video Trimmer
VersionInfoTextVersion={#AppVersion}
VersionInfoCopyright=Copyright (C) 2026

[Files]
Source: "dist\H264ProTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\H264 Pro Trimmer"; Filename: "{app}\H264ProTrimmer.exe"
Name: "{autodesktop}\H264 Pro Trimmer"; Filename: "{app}\H264ProTrimmer.exe"; Tasks: desktopicon

[Tasks]
; ВИДАЛЕНО Flags: unchecked, тепер галочка буде СТОЯТИ по замовчуванню
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\H264ProTrimmer.exe"; Description: "{cm:LaunchProgram,H264 Pro Trimmer}"; Flags: nowait postinstall skipifsilent
#define FileHandle
#define FileLine
#if FileHandle = FileOpen("version.txt")
  #define AppVersionStr FileRead(FileHandle)
  #if FileHandle
    #expr FileClose(FileHandle)
  #endif
#else
  #define AppVersionStr "1.0.0"
#endif

[Setup]
AppId={{PRO-VIDEO-TRIMMER-9911-2024}}
AppName=Pro Video Trimmer
AppVersion={#AppVersionStr}
OutputBaseFilename=ProVideoTrimmer_Setup_v{#AppVersionStr}
DefaultDirName={autopf}\ProVideoTrimmer
DefaultGroupName=Pro Video Trimmer
UninstallDisplayIcon={app}\ProVideoTrimmer.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico

; Метадані (Виправлено назви директив)
VersionInfoCompany=Pro Video Trimmer Project
VersionInfoDescription=Lossless Video Trimmer
VersionInfoTextVersion={#AppVersionStr}
VersionInfoCopyright=Copyright (C) 2026

[Files]
Source: "dist\ProVideoTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Pro Video Trimmer"; Filename: "{app}\ProVideoTrimmer.exe"
Name: "{autodesktop}\Pro Video Trimmer"; Filename: "{app}\ProVideoTrimmer.exe"; Tasks: desktopicon

[Tasks]
; ВИДАЛЕНО Flags: unchecked, тепер галочка буде СТОЯТИ по замовчуванню
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\ProVideoTrimmer.exe"; Description: "{cm:LaunchProgram,Pro Video Trimmer}"; Flags: nowait postinstall skipifsilent
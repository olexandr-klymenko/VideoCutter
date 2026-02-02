; --- Препроцесор для зчитування версії ---
#define FileHandle
#if FileHandle = FileOpen("version.txt")
  #define AppVersionStr FileRead(FileHandle)
  #if FileHandle
    #expr FileClose(FileHandle)
  #endif
#else
  #define AppVersionStr "1.0.0"
#endif

; Визначаємо, чи це бета (шукаємо "beta" в рядку версії)
#define IsBeta Pos("beta", LowerCase(AppVersionStr)) > 0

[Setup]
; --- Автоматичне визначення мови без запитання ---
ShowLanguageDialog=no

; --- Різні AppId для паралельного життя Stable та Beta версій ---
#if IsBeta
  AppId={{PRO-VIDEO-TRIMMER-BETA-ID-9912}}
  AppName=Pro Video Trimmer Beta
  DefaultDirName={autopf}\ProVideoTrimmer Beta
  DefaultGroupName=Pro Video Trimmer Beta
#else
  AppId={{PRO-VIDEO-TRIMMER-9911-2024}}
  AppName=Pro Video Trimmer
  DefaultDirName={autopf}\ProVideoTrimmer
  DefaultGroupName=Pro Video Trimmer
#endif

AppVersion={#AppVersionStr}
AppPublisher=Pro Video Trimmer Project
OutputBaseFilename=ProVideoTrimmer_Setup_v{#AppVersionStr}
UninstallDisplayIcon={app}\ProVideoTrimmer.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico

; Метадані EXE
VersionInfoCompany=Pro Video Trimmer Project
VersionInfoDescription=Lossless Video Trimmer Installer
VersionInfoTextVersion={#AppVersionStr}
VersionInfoCopyright=Copyright (C) 2026

[Languages]
; Перша мова у списку є мовою за замовчуванням (Default)
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Джерело з папки, куди PyInstaller збирає OneDir build
Source: "dist\ProVideoTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Назви ярликів залежать від статусу версії
Name: "{group}\{#IsBeta ? 'Pro Video Trimmer Beta' : 'Pro Video Trimmer'}"; Filename: "{app}\ProVideoTrimmer.exe"
Name: "{autodesktop}\{#IsBeta ? 'Pro Video Trimmer Beta' : 'Pro Video Trimmer'}"; Filename: "{app}\ProVideoTrimmer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ProVideoTrimmer.exe"; Description: "{cm:LaunchProgram,Pro Video Trimmer}"; Flags: nowait postinstall skipifsilent
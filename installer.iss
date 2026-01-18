#include "idp.iss"

[Setup]
AppName=H264 Pro Trimmer
AppVersion=1.0
DefaultDirName={autopf}\H264ProTrimmer
DefaultGroupName=H264 Pro Trimmer
UninstallDisplayIcon={app}\main.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=userdocs:Inno Setup Outputs
OutputBaseFilename=H264Trimmer_Setup
; Вимикаємо стандартну сторінку завершення, щоб встигнути розпакувати FFmpeg (опціонально)
; WizardImageFile=compiler:WizModernImage-IS.bmp

[Files]
; Копіюємо вміст вашої папки збірки (onedir)
Source: "dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\H264 Pro Trimmer"; Filename: "{app}\main.exe"

[Run]
; Запуск після інсталяції
Filename: "{app}\main.exe"; Description: "{cm:LaunchProgram,H264 Pro Trimmer}"; Flags: nowait postinstall skipifsilent

[Code]
var
  FFmpegPath: String;

// 1. Ініціалізація та додавання файлу в чергу завантаження
procedure InitializeWizard;
begin
  FFmpegPath := 'C:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe';

  // Якщо FFmpeg ще не встановлено, налаштовуємо завантаження
  if not FileExists(FFmpegPath) then begin
    idpAddFile('https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.0.1-essentials_build.zip', ExpandConstant('{tmp}\ffmpeg.zip'));

    // Відображати сторінку завантаження
    idpDownloadAfter(wpReady);
  end;
end;

// 2. Розпакування та фінальні налаштування
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ZipPath: String;
  UnzipCmd: String;
begin
  // Виконуємо дії після того, як файли програми вже скопійовані
  if CurStep = ssPostInstall then begin
    ZipPath := ExpandConstant('{tmp}\ffmpeg.zip');

    // Перевіряємо, чи був завантажений архів і чи потрібно його розпакувати
    if FileExists(ZipPath) and (not FileExists(FFmpegPath)) then begin
      // Показуємо користувачу, що йде розпакування (це швидко, тому Refresh вистачить)
      WizardForm.StatusLabel.Caption := 'Розпакування системних компонентів (FFmpeg)...';
      WizardForm.Refresh;

      // Команда розпакування через PowerShell (виконується приховано)
      UnzipCmd := '/c powershell -WindowStyle Hidden -Command "Expand-Archive -Path ''' + ZipPath + ''' -DestinationPath ''C:\'' -Force"';

      if not Exec('cmd.exe', UnzipCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then begin
        MsgBox('Помилка розпакування FFmpeg. Спробуйте встановити його вручну.', mbError, MB_OK);
      end;
    end;

    // 3. Запис шляху у config.ini (використовуємо вбудовану функцію Inno)
    SetIniString('Paths', 'ffmpeg_path', FFmpegPath, ExpandConstant('{app}\config.ini'));

    // 4. Оптимізація Windows Defender (Exclusion)
    // Додаємо папку програми у виключення, щоб PyInstaller не гальмував при старті
    Exec('powershell.exe',
      '-WindowStyle Hidden -Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + '''"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
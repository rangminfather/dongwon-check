; 동원 매입대사 설치 파일 — ISCC /DAppVersion=1.0.0 packaging\installer.iss
; 관리자 권한 없이(사용자 폴더에) 설치되므로 회사 PC에서도 설치할 수 있다.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "동원 매입대사"
#define AppExe "DongwonCheck.exe"

[Setup]
AppId={{8C2B6E4A-3F1D-4C9B-9E57-D0A7F1B2C3E4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=동원F&B
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\DongwonCheck
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=DongwonCheck-Setup-{#AppVersion}
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
WizardImageFile=..\assets\wizard.bmp
WizardSmallImageFile=..\assets\wizard-small.bmp
Compression=lzma2/max
SolidCompression=yes
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[InstallDelete]
; 이전 버전 파일이 남아 충돌하지 않도록 프로그램 폴더를 비우고 새로 깐다.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\DongwonCheck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; 조용한 설치(자동 업데이트)에서도 끝나면 다시 실행한다.
Filename: "{app}\{#AppExe}"; Description: "{#AppName} 실행"; Flags: nowait postinstall

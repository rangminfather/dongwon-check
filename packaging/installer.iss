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
DisableWelcomePage=no
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=DongwonCheck-Setup-{#AppVersion}
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
; 화면 배율별 그림(packaging/make_installer_art.py 로 만들어 커밋해 둔 파일)
WizardImageFile=art\wizard-164.bmp,art\wizard-205.bmp,art\wizard-246.bmp,art\wizard-328.bmp
WizardSmallImageFile=art\wizard-small-55.bmp,art\wizard-small-69.bmp,art\wizard-small-83.bmp,art\wizard-small-110.bmp
WizardImageStretch=no
WizardImageBackColor=$662B07
Compression=lzma2/max
SolidCompression=yes
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Messages]
korean.WelcomeLabel1=[name] 설치를 시작합니다
korean.WelcomeLabel2=동원 원장과 거래처 매입자료를 일자 · 바코드 · 수량 · 단가 · 금액으로 자동 대사하는 프로그램입니다.%n%n관리자 권한 없이 설치되며, 새 버전이 나오면 프로그램이 알려 드립니다.
korean.FinishedHeadingLabel=설치가 끝났습니다
korean.FinishedLabel=[name] 을(를) 바로 사용할 수 있습니다.%n원장과 거래처 파일을 끌어놓고 [비교 실행]을 눌러 보세요.

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[InstallDelete]
; 이전 버전 파일이 남아 충돌하지 않도록 프로그램 폴더를 비우고 새로 깐다.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\DongwonCheck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autoprograms}\{#AppName}\{#AppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; 앱 설정(창 크기·최근 폴더 등). 제거할 때 함께 지운다.
Root: HKCU; Subkey: "Software\DongwonFNB"; Flags: uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{%TEMP}\DongwonCheck"

[Run]
; 조용한 설치(자동 업데이트)에서도 끝나면 다시 실행한다.
Filename: "{app}\{#AppExe}"; Description: "{#AppName} 실행"; Flags: nowait postinstall

[Code]
{ 이미 설치된 PC에서 설치 파일을 열면 '업데이트 / 새로 설치 / 삭제' 중에서 고르게 한다.
  자동 업데이트(/SILENT)는 이 화면을 건너뛰고 기본값(업데이트)으로 진행된다. }
const
  UninstKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8C2B6E4A-3F1D-4C9B-9E57-D0A7F1B2C3E4}_is1';
var
  ModePage: TInputOptionWizardPage;
  InstalledVer: String;
  Quitting: Boolean;

procedure InitializeWizard;
begin
  if RegQueryStringValue(HKCU, UninstKey, 'DisplayVersion', InstalledVer) then
  begin
    ModePage := CreateInputOptionPage(wpWelcome,
      '작업 선택',
      '이 PC에 이미 설치되어 있습니다 (현재 v' + InstalledVer + '  →  설치 파일 v{#AppVersion})',
      '원하는 작업을 고른 뒤 [다음]을 누르세요.',
      True, False);
    ModePage.Add('업데이트 (수정 설치) — 설정은 그대로 두고 새 버전으로 바꿉니다');
    ModePage.Add('새로 설치 — 설정(최근 폴더·비교 기준 등)을 지우고 처음 상태로 설치합니다');
    ModePage.Add('프로그램 삭제 — 이 PC에서 동원 매입대사를 지웁니다 (결과 엑셀 파일은 남습니다)');
    ModePage.SelectedValueIndex := 0;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Uninst: String;
  Code: Integer;
begin
  Result := True;
  if (ModePage <> nil) and (CurPageID = ModePage.ID) and (ModePage.SelectedValueIndex = 2) then
  begin
    Result := False;
    if MsgBox('동원 매입대사를 이 PC에서 삭제할까요?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      if RegQueryStringValue(HKCU, UninstKey, 'UninstallString', Uninst) then
        Exec(RemoveQuotes(Uninst), '/SILENT /SUPPRESSMSGBOXES', '', SW_SHOW, ewWaitUntilTerminated, Code);
      MsgBox('삭제를 진행했습니다. 설치 창을 닫습니다.', mbInformation, MB_OK);
      Quitting := True;
      WizardForm.Close;
    end;
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if Quitting then
    Confirm := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  { '새로 설치'를 골랐으면 설치 직전에 앱 설정을 지운다. }
  if (CurStep = ssInstall) and (ModePage <> nil) and (ModePage.SelectedValueIndex = 1) then
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\DongwonFNB');
end;

# Development-only registration of the .igz Explorer thumbnail handler (HKCU).
# No admin needed. Restart Explorer (or log off/on) after registering.
#
#   powershell -ExecutionPolicy Bypass -File installer\register_user.ps1
#   powershell -ExecutionPolicy Bypass -File installer\register_user.ps1 -Unregister
param([switch]$Unregister)

$ErrorActionPreference = 'Stop'

$clsid = '{A4C84E91-2E97-4D99-8FE5-E8B2B7D60D2B}'
$thumbnailHandler = '{e357fccd-a995-4576-b01f-234630154e96}'
$dllPath = Join-Path $PSScriptRoot 'IngeTrazoThumbnailProvider.dll'
$assocPath = "HKCU:\Software\Classes\.igz\ShellEx\$thumbnailHandler"
$clsidPath = "HKCU:\Software\Classes\CLSID\$clsid"

if ($Unregister) {
    Remove-Item -Path $assocPath -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $clsidPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host 'Registro de desenvolvimento removido (HKCU).'
    return
}

if (-Not (Test-Path $dllPath)) {
    throw "DLL not found: $dllPath - run installer\build-thumbnail-provider.ps1"
}
$codeBase = ([System.Uri]$dllPath).AbsoluteUri

New-Item -Path $assocPath -Force -Value $clsid | Out-Null

New-Item -Path $clsidPath -Force -Value 'IngeTrazo Thumbnail Provider' | Out-Null
$inproc = New-Item -Path "$clsidPath\InprocServer32" -Force `
    -Value 'mscoree.dll'
Set-ItemProperty -Path $inproc.PSPath -Name 'ThreadingModel' -Value 'Both'
Set-ItemProperty -Path $inproc.PSPath -Name 'Class' `
    -Value 'IngeTrazo.Shell.IngeTrazoThumbnailProvider'
Set-ItemProperty -Path $inproc.PSPath -Name 'Assembly' `
    -Value 'IngeTrazoThumbnailProvider, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null'
Set-ItemProperty -Path $inproc.PSPath -Name 'RuntimeVersion' -Value 'v4.0.30319'
Set-ItemProperty -Path $inproc.PSPath -Name 'CodeBase' -Value $codeBase

Write-Host "Registrado no HKCU: $codeBase"
Write-Host 'Reinicie o Explorer para atualizar as miniaturas em cache.'

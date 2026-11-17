# Rebuilds installer\IngeTrazoThumbnailProvider.dll from the C# source.
# The DLL is a generated artifact (see .gitignore): CI runs this before Inno
# Setup, and local installer builds must run it once as well.
#
#   powershell -ExecutionPolicy Bypass -File installer\build-thumbnail-provider.ps1
$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'IngeTrazoThumbnailProvider.cs'
$output = Join-Path $PSScriptRoot 'IngeTrazoThumbnailProvider.dll'
if (-Not (Test-Path $source)) { throw "Fuente no encontrada: $source" }

# .NET Framework 4.x ships csc.exe (Roslyn) with the runtime on every modern
# Windows. Prefer the 64-bit one; the 32-bit compiler emits the same MSIL.
$framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$csc = Join-Path $framework 'csc.exe'
if (-Not (Test-Path $csc)) {
    $framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319'
    $csc = Join-Path $framework 'csc.exe'
}
if (-Not (Test-Path $csc)) { throw 'csc.exe de .NET Framework no encontrado' }

$references = @('mscorlib.dll', 'System.dll', 'System.Core.dll',
                'System.Drawing.dll', 'System.IO.Compression.dll') |
    ForEach-Object { '/r:' + (Join-Path $framework $_) }

& $csc /nologo /target:library /platform:anycpu /optimize+ `
    /out:"$output" @references "$source"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$name = [System.Reflection.AssemblyName]::GetAssemblyName($output)
if ($name.Version.ToString() -ne '1.0.0.0') {
    throw "Unexpected DLL version: $($name.Version) (registration uses 1.0.0.0)"
}
Write-Host "OK: $output - $($name.FullName)"

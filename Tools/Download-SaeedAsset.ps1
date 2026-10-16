# Downloads the canonical Saeed GLB from this Fortnite repository.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$assetDir = Join-Path $repoRoot 'assets'
$destination = Join-Path $assetDir 'saeed.glb'
$url = 'https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/assets/saeed.glb'

New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
$tempFile = Join-Path $assetDir 'saeed.glb.download'
try {
    Invoke-WebRequest -Uri $url -OutFile $tempFile
    $stream = [System.IO.File]::OpenRead($tempFile)
    try {
        $magic = New-Object byte[] 4
        if ($stream.Read($magic, 0, 4) -ne 4) { throw 'Downloaded file is too short.' }
    } finally {
        $stream.Dispose()
    }
    if ([System.Text.Encoding]::ASCII.GetString($magic) -ne 'glTF') {
        throw 'Downloaded file does not have the GLB glTF header.'
    }
    $hash = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash
    Move-Item -Force -Path $tempFile -Destination $destination
    Write-Output "Saved canonical Saeed asset: $destination"
    Write-Output "SHA-256: $hash"
} finally {
    if (Test-Path $tempFile) { Remove-Item -Force $tempFile }
}

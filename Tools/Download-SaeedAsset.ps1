# Downloads the Saeed GLB from the source repository into this working repo.
# If Saeed-V2.0 is private, set GH_TOKEN to a token that can read that repository.
# This script is for project setup on Windows; it is not required by players.
[CmdletBinding()]
param(
    [string]$Owner = "saeedhub101",
    [string]$SourceRepository = "Saeed-V2.0",
    [string]$SourceBranch = "main",
    [string]$AssetPath = "assets/Saeed_AI-3D.glb",
    [string]$Destination = "assets/Saeed_AI-3D.glb"
)

$ErrorActionPreference = "Stop"
$apiUrl = "https://api.github.com/repos/$Owner/$SourceRepository/contents/$AssetPath" +
          "?ref=$([uri]::EscapeDataString($SourceBranch))"
$headers = @{
    "Accept" = "application/vnd.github.raw+json"
    "User-Agent" = "Saeed-Fortnite-asset-setup"
}
if ($env:GH_TOKEN) {
    $headers["Authorization"] = "Bearer $env:GH_TOKEN"
}

$destinationPath = [System.IO.Path]::GetFullPath($Destination)
$destinationDirectory = Split-Path -Parent $destinationPath
New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null

Write-Host "Downloading the GLB asset from $Owner/$SourceRepository (branch: $SourceBranch)..."
try {
    Invoke-WebRequest -Uri $apiUrl -Headers $headers -OutFile $destinationPath
}
catch {
    Remove-Item -LiteralPath $destinationPath -Force -ErrorAction SilentlyContinue
    throw "Asset download failed. Confirm the source repository/path and, if private, set GH_TOKEN with read access. Original error: $($_.Exception.Message)"
}

$stream = [System.IO.File]::OpenRead($destinationPath)
try {
    if ($stream.Length -lt 12) {
        throw "Downloaded file is too small to be a valid GLB."
    }
    $header = New-Object byte[] 4
    [void]$stream.Read($header, 0, 4)
    $magic = [System.Text.Encoding]::ASCII.GetString($header)
    if ($magic -ne "glTF") {
        throw "Downloaded content does not start with the GLB magic 'glTF'. Check access permissions; GitHub may have returned an error page."
    }
}
finally {
    $stream.Dispose()
}

$hash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item -LiteralPath $destinationPath).Length
Write-Host "Asset downloaded and header checked."
Write-Host "Path: $destinationPath"
Write-Host "Size bytes: $size"
Write-Host "SHA-256: $hash"
Write-Host "Next: run python Tools/validate_glb.py $destinationPath --json"

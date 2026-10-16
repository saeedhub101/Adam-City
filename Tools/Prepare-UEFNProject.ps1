[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$project = (Resolve-Path -LiteralPath $ProjectPath).Path

$projectFiles = @(Get-ChildItem -LiteralPath $project -Filter '*.uefnproject' -File -ErrorAction SilentlyContinue)
if ($projectFiles.Count -eq 0) {
    throw "No .uefnproject file found in '$project'. Create a Blank island project in UEFN first; this helper will not invent native project metadata."
}
if ($projectFiles.Count -gt 1) {
    throw "More than one .uefnproject file found in '$project'. Pass the exact UEFN project folder."
}

$projectName = [IO.Path]::GetFileNameWithoutExtension($projectFiles[0].Name)
$pluginContent = Join-Path $project ("Plugins\{0}\Content" -f $projectName)
if (-not (Test-Path -LiteralPath $pluginContent -PathType Container)) {
    throw "Expected Verse content folder '$pluginContent' was not found. Open the project in UEFN and use Verse Explorer to create a Verse file first, then close UEFN and rerun."
}

$sourceVerse = Join-Path $repoRoot 'Verse\saeed_npc_behavior.verse'
if (-not (Test-Path -LiteralPath $sourceVerse -PathType Leaf)) {
    throw "Source Verse file not found: $sourceVerse"
}

$destinationVerse = Join-Path $pluginContent 'saeed_npc_behavior.verse'
if (Test-Path -LiteralPath $destinationVerse -PathType Leaf) {
    $backup = "$destinationVerse.bak"
    Copy-Item -LiteralPath $destinationVerse -Destination $backup -Force
    Write-Host "Backed up existing file to $backup"
}

Copy-Item -LiteralPath $sourceVerse -Destination $destinationVerse -Force
Write-Host "Copied Saeed Verse source to: $destinationVerse"
Write-Host "Next: reopen UEFN, run Verse > Build Verse Code, resolve compiler diagnostics, configure NPC Character Definition/Spawner, and playtest."
Write-Warning "This script does not import or convert the GLB and does not prove that a custom mesh is supported by the NPC system."

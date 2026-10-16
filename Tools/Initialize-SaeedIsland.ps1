[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string]$ProjectPath,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$projectFiles = @(Get-ChildItem -LiteralPath $project -Filter '*.uefnproject' -File -ErrorAction SilentlyContinue)
if ($projectFiles.Count -ne 1) {
    throw "Expected exactly one .uefnproject in '$project'. Create a Blank project named SaeedIsland in UEFN first."
}

$projectName = [IO.Path]::GetFileNameWithoutExtension($projectFiles[0].Name)
if ($projectName -ne 'SaeedIsland') {
    Write-Warning "Project is named '$projectName', not 'SaeedIsland'. Continuing with its actual name."
}
$pluginContent = Join-Path $project ("Plugins\{0}\Content" -f $projectName)
if (-not (Test-Path -LiteralPath $pluginContent -PathType Container)) {
    throw "Missing '$pluginContent'. Open the project in UEFN, create a Verse file using Verse Explorer, then close UEFN and retry."
}

$sourceAsset = Join-Path $repoRoot 'assets\saeed.glb'
$sourceVerse = Join-Path $repoRoot 'Verse\saeed_npc_behavior.verse'
foreach ($source in @($sourceAsset, $sourceVerse)) {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required source file is missing: $source" }
}

$importDir = Join-Path $pluginContent 'Imports\Saeed'
$verseDir = Join-Path $pluginContent 'SaeedIsland'
New-Item -ItemType Directory -Path $importDir -Force | Out-Null
New-Item -ItemType Directory -Path $verseDir -Force | Out-Null

$assetDestination = Join-Path $importDir 'saeed.glb'
$verseDestination = Join-Path $verseDir 'saeed_npc_behavior.verse'
foreach ($pair in @(
    @{ Source = $sourceAsset; Destination = $assetDestination },
    @{ Source = $sourceVerse; Destination = $verseDestination }
)) {
    if ((Test-Path -LiteralPath $pair.Destination) -and -not $Force) {
        throw "Destination already exists: $($pair.Destination). Use -Force to back it up and replace it."
    }
    if (Test-Path -LiteralPath $pair.Destination) {
        Copy-Item -LiteralPath $pair.Destination -Destination ($pair.Destination + '.bak') -Force
    }
    if ($PSCmdlet.ShouldProcess($pair.Destination, 'Copy Saeed project file')) {
        Copy-Item -LiteralPath $pair.Source -Destination $pair.Destination -Force
    }
}

$manifest = @"
# SaeedIsland local setup record

- UEFN project: $($projectFiles[0].FullName)
- Original character source: $assetDestination
- Verse starter: $verseDestination
- Status: files staged; GLB import, NPC appearance assignment, Verse compilation, and in-game playtest are NOT confirmed.
- Next: import the GLB through UEFN Content Browser if the installed version accepts GLB. If it does not, convert the source in Blender to a supported FBX with a verified humanoid skeleton. Then create/configure an NPC Character Definition and NPC Spawner, attach the Verse behavior, build Verse, and playtest.
"@
$manifestPath = Join-Path $project 'SAEED-ISLAND-SETUP.md'
if ((Test-Path -LiteralPath $manifestPath) -and -not $Force) {
    throw "Manifest already exists: $manifestPath. Use -Force to replace it."
}
if ($PSCmdlet.ShouldProcess($manifestPath, 'Write setup manifest')) {
    Set-Content -LiteralPath $manifestPath -Value $manifest -Encoding utf8
}

Write-Host "SaeedIsland files staged in: $project"
Write-Host "Character asset copied only as a source file; this does not import it into UEFN."
Write-Host "Build Verse and test the NPC in UEFN before treating the island as functional."

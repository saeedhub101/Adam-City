# Downloads a real, existing UEFN project (including its .uefnproject and .umap)
# and stages Saeed's character assets beside it. Does not pretend to compile/build the island.
[CmdletBinding()]
param(
    [string]$Destination = (Join-Path (Get-Location) 'SaeedIsland-Base'),
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/pheobus78/UEFN_ForTemple'
$archive = 'https://github.com/pheobus78/UEFN_ForTemple/archive/refs/heads/main.zip'
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ('SaeedIsland-UEFN-' + [guid]::NewGuid().ToString('N'))
$zip = Join-Path $temp 'project.zip'
$extract = Join-Path $temp 'extract'
try {
    if ((Test-Path $Destination) -and -not $Force) {
        throw "Destination already exists: $Destination . Use -Force only if you want it replaced."
    }
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    Invoke-WebRequest -Uri $archive -OutFile $zip
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
    $root = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
    if (-not $root) { throw 'Downloaded archive did not contain a root folder.' }
    $source = Join-Path $root.FullName 'ForTemple'
    $project = Join-Path $source 'ForTemple.uefnproject'
    $map = Join-Path $source 'Plugins\ForTemple\Content\ForTemple.umap'
    if (-not (Test-Path $project)) { throw 'The downloaded archive is missing ForTemple.uefnproject.' }
    if (-not (Test-Path $map)) { throw 'The downloaded archive is missing the actual ForTemple.umap map.' }
    if (Test-Path $Destination) { Remove-Item -LiteralPath $Destination -Recurse -Force }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination (Join-Path $Destination 'ForTemple') -Recurse
    $assetDir = Join-Path $Destination 'Saeed-Assets'
    New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
    Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/assets/saeed.glb' -OutFile (Join-Path $assetDir 'saeed.glb')
    $glb = Join-Path $assetDir 'saeed.glb'
    $stream = [System.IO.File]::OpenRead($glb)
    try {
        $magic = New-Object byte[] 4
        if ($stream.Read($magic, 0, 4) -ne 4 -or [System.Text.Encoding]::ASCII.GetString($magic) -ne 'glTF') {
            throw 'Downloaded Saeed model is not a valid GLB file.'
        }
    } finally { $stream.Dispose() }
    @"
# SaeedIsland working base

Downloaded source: $repo
Project: ForTemple/ForTemple.uefnproject
Map asset: ForTemple/Plugins/ForTemple/Content/ForTemple.umap
Saeed model: Saeed-Assets/saeed.glb

This is a real UEFN project archive, not a newly fabricated project. Keep the source project/plugin names unchanged initially: renaming Unreal package paths without resaving in UEFN can break asset references. Open the .uefnproject in UEFN, then use UEFN's supported project workflow to create/rename your working copy to SaeedIsland. Import Saeed-Assets/saeed.glb through the editor if supported; otherwise convert it to a supported skeletal/static mesh format first.

Upstream README says the author open-sourced project/map resources, but the repository does not include a clear LICENSE file. Treat this as a personal working base; verify permission before redistributing the project or publishing derivative source assets.
"@ | Set-Content -LiteralPath (Join-Path $Destination 'SAEED-ISLAND-BASE-INFO.md') -Encoding UTF8
    Write-Output "SUCCESS: Existing UEFN project and map staged at: $Destination"
    Write-Output "Open: $(Join-Path $Destination 'ForTemple\ForTemple.uefnproject')"
    Write-Output 'Saeed GLB downloaded and header-validated.'
} finally {
    if (Test-Path $temp) { Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue }
}

param(
    [string]$GameRoot = 'E:\SteamLibrary\steamapps\common\ProjectZomboid',
    [string]$MiningRoot = 'E:\git\PZMining'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$outputRoot = Join-Path $PSScriptRoot 'render-audit'
$classRoot = Join-Path $outputRoot 'classes'
$sourceRoot = Join-Path $outputRoot 'source'
New-Item -ItemType Directory -Path $classRoot,$sourceRoot -Force | Out-Null
$classes = @(
    'zombie/core/skinnedmodel/model/IsoObjectModelDrawer',
    'zombie/core/skinnedmodel/model/IsoObjectAnimations',
    'zombie/core/skinnedmodel/model/ModelMesh',
    'zombie/core/skinnedmodel/model/Model',
    'zombie/core/skinnedmodel/model/FileTask_LoadMesh',
    'zombie/core/skinnedmodel/model/FileTask_AbstractLoadModel',
    'zombie/core/skinnedmodel/model/AiSceneAssetManager',
    'zombie/core/skinnedmodel/model/jassimp/JAssImpImporter',
    'zombie/core/skinnedmodel/model/jassimp/ProcessedAiScene',
    'zombie/core/skinnedmodel/model/jassimp/ImportedStaticMesh',
    'zombie/core/skinnedmodel/model/jassimp/ImportedSkinnedMesh',
    'zombie/core/skinnedmodel/model/VertexBufferObject',
    'zombie/core/skinnedmodel/shader/Shader',
    'zombie/core/skinnedmodel/ModelCamera',
    'zombie/core/skinnedmodel/ModelManager',
    'zombie/core/textures/Texture',
    'zombie/core/textures/TextureID',
    'zombie/iso/SpriteModel',
    'zombie/iso/fboRenderChunk/FBORenderChunkCamera',
    'zombie/iso/fboRenderChunk/FBORenderChunk',
    'zombie/iso/fboRenderChunk/FBORenderLevels',
    'zombie/scripting/objects/ModelScript',
    'zombie/core/opengl/ShaderProgram',
    'zombie/core/Core',
    'zombie/iso/IsoUtils'
)
$jar = Join-Path $GameRoot 'projectzomboid.jar'
$zip = [IO.Compression.ZipFile]::OpenRead($jar)
$manifest = [Collections.Generic.List[string]]::new()
$manifest.Add('Current game JAR SHA256: ' + (Get-FileHash -LiteralPath $jar).Hash)
try {
    foreach ($entry in $zip.Entries) {
        $stem = $entry.FullName -replace '\.class$',''
        $outer = ($stem -split '\$')[0]
        if ($entry.FullName.EndsWith('.class') -and $classes -contains $outer) {
            $destination = Join-Path $classRoot $entry.FullName
            New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$destination,$true)
            $old = Join-Path (Join-Path $MiningRoot 'extracted') $entry.FullName
            $state = if (Test-Path -LiteralPath $old) {
                if ((Get-FileHash -LiteralPath $old).Hash -eq (Get-FileHash -LiteralPath $destination).Hash) {'same'} else {'different'}
            } else {'missing'}
            $manifest.Add($entry.FullName + ' PZMining=' + $state)
        }
    }
} finally { $zip.Dispose() }
$manifest | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.txt')
$java = Join-Path $GameRoot 'jre64/bin/java.exe'
$cfr = Join-Path $MiningRoot 'tools/cfr.jar'
foreach ($class in $classes) {
    $path = Join-Path $classRoot ($class + '.class')
    if (Test-Path -LiteralPath $path) {
        & $java -jar $cfr $path --outputdir $sourceRoot --silent true
        if ($LASTEXITCODE -ne 0) { throw "CFR failed: $class" }
    }
}
Write-Output ('Extracted/decompiled ' + $classes.Count + ' render classes from the installed game.')
$manifest | Select-Object -First 8

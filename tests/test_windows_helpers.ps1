$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$resize = Join-Path $repo 'skills/codex-fleet/scripts/Resize-Image.ps1'
$awake = Join-Path $repo 'skills/codex-fleet/scripts/Invoke-KeepAwake.ps1'
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('codex-fleet-İ test-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    foreach ($script in @($resize, $awake)) {
        $parseErrors = $null; $tokens = $null
        [System.Management.Automation.Language.Parser]::ParseFile($script, [ref]$tokens, [ref]$parseErrors) | Out-Null
        if ($parseErrors.Count) { throw "Parse errors in $script : $parseErrors" }
    }
    Add-Type -AssemblyName System.Drawing
    $inputImage = Join-Path $tempRoot 'input.png'
    $bitmap = [Drawing.Bitmap]::new(900, 300)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([Drawing.Color]::Red)
        $graphics.FillRectangle([Drawing.Brushes]::Blue, 300, 0, 300, 300)
        $bitmap.Save($inputImage, [Drawing.Imaging.ImageFormat]::Png)
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
    $hashBefore = (Get-FileHash $inputImage).Hash
    foreach ($case in @(
        @{Width=300; Height=0; Crop=$false; ExpectedW=300; ExpectedH=100},
        @{Width=300; Height=300; Crop=$false; ExpectedW=300; ExpectedH=100},
        @{Width=0; Height=100; Crop=$false; ExpectedW=300; ExpectedH=100},
        @{Width=256; Height=256; Crop=$true; ExpectedW=256; ExpectedH=256},
        @{Width=1; Height=0; Crop=$false; ExpectedW=1; ExpectedH=1}
    )) {
        $outImage = Join-Path $tempRoot ([guid]::NewGuid().ToString() + '.png')
        & $resize -Path $inputImage -Out $outImage -Width $case.Width -Height $case.Height -Crop:$case.Crop
        $result = [Drawing.Bitmap]::new($outImage)
        try {
            if ($result.Width -ne $case.ExpectedW -or $result.Height -ne $case.ExpectedH) {
                throw "Wrong output dimensions: $($result.Width)x$($result.Height)"
            }
            if ($case.Crop -and $result.GetPixel(128,128).B -lt 240) { throw 'Crop is not centered' }
        } finally { $result.Dispose() }
    }
    $rejected = $false
    try { & $resize -Path $inputImage -Out $inputImage -Width 300 } catch { $rejected = $true }
    if (-not $rejected) { throw 'In-place overwrite was allowed' }
    if ((Get-FileHash $inputImage).Hash -ne $hashBefore) { throw 'Source image changed' }
    $rejected = $false
    try { & $resize -Path $inputImage -Out (Join-Path $tempRoot 'bad.png') -Width -1 -Height 30 } catch { $rejected = $true }
    if (-not $rejected) { throw 'Negative dimension accepted' }

    # Exercise the actual native Windows call in an isolated sentinel process.
    $stdout = Join-Path $tempRoot 'awake.log'
    $stderr = Join-Path $tempRoot 'awake.err'
    $proc = Start-Process pwsh -ArgumentList @('-NoProfile', '-File', ('"' + $awake + '"'), '-Minutes', '1') -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    try {
        $ready = $false
        for ($i=0; $i -lt 40; $i++) {
            Start-Sleep -Milliseconds 250
            if ((Get-Content $stdout -Raw) -match 'KEEPAWAKE_ON') { $ready = $true; break }
            if ($proc.HasExited) { break }
        }
        if (-not $ready -or $proc.HasExited) { throw "Sleep block failed: $(Get-Content $stderr -Raw)" }
    } finally {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force; $proc.WaitForExit() }
        $proc.Dispose()
    }
    Write-Output 'PASS: parser, resize/fit/crop/tiny image, source preservation, input validation, native sleep request'
} finally { Remove-Item -LiteralPath $tempRoot -Recurse -Force }

<#
.SYNOPSIS
    Windows equivalent of macOS `sips -z` / `sips -c` — scale or centre-crop a generated image.

.DESCRIPTION
    `gpt-image-2` rejects small sizes (below the 655,360-pixel minimum), so the documented
    workflow is to generate at a supported size and downscale afterwards. On macOS that is
    `sips`; Windows ships no equivalent, and ImageMagick is not a safe assumption.

    This uses System.Drawing from the .NET base library — no install, no dependency. It never
    modifies the source file; output always goes to -Out.

    Without -Crop it scales to fit the requested box (`sips -z`). With -Crop it first crops the
    source from the centre to the target aspect ratio, then scales (`sips -c`), so the subject
    stays centred and the output is never letterboxed or distorted.

    Supply only -Width or only -Height to preserve the source aspect ratio.

.PARAMETER Path
    Source image. PNG or JPEG.

.PARAMETER Out
    Destination path. Format follows the extension (.jpg/.jpeg -> JPEG, anything else -> PNG).
    Parent directories are created if missing.

.PARAMETER Width
    Target width in pixels. Optional if -Height is given.

.PARAMETER Height
    Target height in pixels. Optional if -Width is given.

.PARAMETER Crop
    Centre-crop to the target aspect ratio before scaling.

.EXAMPLE
    pwsh -NoProfile -File skills/codex-fleet/scripts/Resize-Image.ps1 -Path hero.png -Out hero-512.png -Width 512

    Downscale to 512px wide, height follows the source ratio.

.EXAMPLE
    pwsh -NoProfile -File skills/codex-fleet/scripts/Resize-Image.ps1 -Path wide.png -Out icon.png -Width 1024 -Height 1024 -Crop

    Centre-crop a landscape render to square, then scale to 1024x1024.

.OUTPUTS
    RESIZED <path> <width>x<height> bytes=<n>
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Out,
    [ValidateRange(0, 32768)][int]$Width = 0,
    [ValidateRange(0, 32768)][int]$Height = 0,
    [switch]$Crop
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This helper requires Windows and PowerShell 7+.' }
if ($Width -le 0 -and $Height -le 0) { throw 'Supply -Width, -Height, or both.' }

$sourcePath = (Resolve-Path -LiteralPath $Path).Path
$outputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
if ([string]::Equals($sourcePath, $outputPath, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Source and destination must be different files.'
}
if ($Crop -and ($Width -eq 0 -or $Height -eq 0)) { throw '-Crop requires both -Width and -Height.' }
Add-Type -AssemblyName System.Drawing

$src = [System.Drawing.Image]::FromFile($sourcePath)
try {
    if (-not $Crop) {
        $scale = if ($Width -eq 0) { $Height / $src.Height }
                 elseif ($Height -eq 0) { $Width / $src.Width }
                 else { [Math]::Min($Width / $src.Width, $Height / $src.Height) }
        $Width = [Math]::Max(1, [int][Math]::Round($src.Width * $scale))
        $Height = [Math]::Max(1, [int][Math]::Round($src.Height * $scale))
    }

    # Source rectangle. With -Crop, narrow it to the target aspect ratio about the centre.
    $sx = 0; $sy = 0; $sw = $src.Width; $sh = $src.Height
    if ($Crop) {
        $targetRatio = $Width / $Height
        $sourceRatio = $src.Width / $src.Height
        if ($sourceRatio -gt $targetRatio) {
            $sw = [Math]::Max(1, [int][Math]::Round($src.Height * $targetRatio))
            $sx = [int][Math]::Round(($src.Width - $sw) / 2)
        } else {
            $sh = [Math]::Max(1, [int][Math]::Round($src.Width / $targetRatio))
            $sy = [int][Math]::Round(($src.Height - $sh) / 2)
        }
    }

    $dst = New-Object System.Drawing.Bitmap($Width, $Height)
    try {
        $g = [System.Drawing.Graphics]::FromImage($dst)
        try {
            $g.InterpolationMode  = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.PixelOffsetMode    = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $g.SmoothingMode      = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            $g.Clear([System.Drawing.Color]::Transparent)
            $g.DrawImage($src,
                (New-Object System.Drawing.Rectangle(0, 0, $Width, $Height)),
                $sx, $sy, $sw, $sh,
                [System.Drawing.GraphicsUnit]::Pixel)
        } finally { $g.Dispose() }

        $outDir = Split-Path -Parent $Out
        if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        }
        $format = if ([IO.Path]::GetExtension($Out) -match '^\.jpe?g$') {
            [System.Drawing.Imaging.ImageFormat]::Jpeg
        } else {
            [System.Drawing.Imaging.ImageFormat]::Png
        }
        $dst.Save($outputPath, $format)
    } finally { $dst.Dispose() }
} finally { $src.Dispose() }

$info = Get-Item -LiteralPath $Out
Write-Output "RESIZED $($info.FullName) ${Width}x${Height} bytes=$($info.Length)"

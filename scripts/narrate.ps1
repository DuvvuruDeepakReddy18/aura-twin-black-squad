param([string]$Narration, [string]$AudioDirectory, [int]$Rate = 2)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force -Path $AudioDirectory | Out-Null
$chapters = Get-Content -LiteralPath $Narration -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($chapter in $chapters) {
    $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $speaker.SelectVoice('Microsoft Zira Desktop')
    $speaker.Rate = $Rate
    $speaker.Volume = 100
    $target = Join-Path $AudioDirectory ('slide-{0:D2}.wav' -f [int]$chapter.slide)
    $speaker.SetOutputToWaveFile($target)
    $speaker.Speak($chapter.text)
    $speaker.Dispose()
    Write-Output ('Narrated slide {0}: {1}' -f $chapter.slide, $chapter.title)
}

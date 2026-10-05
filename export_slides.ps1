$ppt = New-Object -ComObject PowerPoint.Application
$filePath = "D:\hackfest\Hackfest_2026_Screening_Presentation.pptx"
$outDir = "D:\hackfest\slide_images"
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$pres = $ppt.Presentations.Open($filePath, 1, 0, 0)
$pres.SaveAs($outDir, 17)
$pres.Close()
$ppt.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
Write-Host "Export complete. Files in ${outDir}:"
Get-ChildItem $outDir | Select-Object Name, Length

# Keep capturing on the hotspot adapter for $Seconds, restarting tshark whenever
# the adapter goes down (hotspot toggled off/on) so the boiler's reconnect is caught.
param([int]$Seconds = 300, [string]$Prefix = "reconnect")

$tshark = "C:\Program Files\Wireshark\tshark.exe"
$iface = "\Device\NPF_{12379F2E-D466-446F-905E-1B94E3A4A204}"
$captures = Join-Path (Split-Path $PSScriptRoot) "captures"
$deadline = (Get-Date).AddSeconds($Seconds)
$n = 0

while ((Get-Date) -lt $deadline) {
    $left = [int]($deadline - (Get-Date)).TotalSeconds
    if ($left -lt 2) { break }
    $n++
    $out = Join-Path $captures ("{0}_{1:D2}.pcapng" -f $Prefix, $n)
    & $tshark -i $iface -f "ether host 04:78:63:a6:e1:4a or port 53 or port 67 or port 68" -a duration:$left -w $out -q 2>$null
    Start-Sleep -Milliseconds 1500
}
Get-ChildItem $captures -Filter "${Prefix}_*.pcapng" | Where-Object Length -gt 200 | Select-Object Name, Length

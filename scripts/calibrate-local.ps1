$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$out=Join-Path $projectRoot ('runs\calibration-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.json')
$image=(& docker image inspect python:3.12-slim --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Docker image unavailable' }
$argsList=@('run','--rm','--read-only','--network','none','--pids-limit','128','--memory','512m',
 '--cpus','2','--cap-drop','ALL','--security-opt','no-new-privileges=true',
 '--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/app:rw,nosuid,nodev,size=1m,mode=700',
 '--workdir','/app','--env','PYTHONDONTWRITEBYTECODE=1')
foreach ($cap in @('SETUID','SETGID','SETPCAP','CHOWN','KILL')) { $argsList+=@('--cap-add',$cap) }
foreach ($dir in @('fixture','tests','probes','evaluation','contracts')) {
 $argsList+=@('--mount',"type=bind,source=$projectRoot\$dir,target=/app/$dir,readonly")
}
$argsList+=@($image,'python','-m','probes.calibrate_recovery')
& docker @argsList | Set-Content -LiteralPath $out
if ($LASTEXITCODE -ne 0) { throw "Calibration failed: $out" }
Write-Output "Calibration: $out"

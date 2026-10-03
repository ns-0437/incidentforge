param([Parameter(Mandatory=$true)][string]$Execution)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$path=(Resolve-Path -LiteralPath $Execution).Path
$receipt=Get-Content -LiteralPath (Join-Path $path 'receipt.json') -Raw | ConvertFrom-Json
$image=(& docker image inspect python:3.12-slim --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Docker image unavailable' }
$argsList=@('run','--rm','--read-only','--network','none','--pids-limit','32','--memory','256m',
 '--cpus','1','--cap-drop','ALL','--security-opt','no-new-privileges=true',
 '--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--workdir','/app',
 '--env','PYTHONDONTWRITEBYTECODE=1','--mount',"type=bind,source=$path,target=/input,readonly")
foreach ($dir in @('probes','evaluation')) { $argsList+=@('--mount',"type=bind,source=$projectRoot\$dir,target=/app/$dir,readonly") }
$argsList+=@($image,'python','-m','probes.verify_candidate_archive','/input/evidence.zip',$receipt.sha256)
& docker @argsList | Set-Content -LiteralPath (Join-Path $path 'independent-verification.json')
if ($LASTEXITCODE -ne 0) { throw 'Independent verification failed' }
Get-Content -LiteralPath (Join-Path $path 'independent-verification.json')

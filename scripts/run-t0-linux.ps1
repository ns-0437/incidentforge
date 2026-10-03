param(
    [string]$Image = 'python:3.12-slim',
    [switch]$PullImage,
    [ValidateSet('t0','t1','t2','t6')][string]$Stage = 't0'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$resultDir = Join-Path $projectRoot ('runs\' + $Stage + '-linux-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $resultDir -Force | Out-Null

function Require-DockerSuccess([string]$label) {
    if ($LASTEXITCODE -ne 0) { throw "$label failed (exit $LASTEXITCODE)." }
}

$server = & docker version --format '{{json .Server}}' 2>&1
if ($LASTEXITCODE -ne 0) {
    $server | Set-Content -LiteralPath (Join-Path $resultDir 'runtime-error.txt')
    throw 'Docker engine is unavailable. No Linux checks ran. Start/fix Docker Desktop first; do not reset/delete project data.'
}
if ($PullImage) {
    & docker pull $Image
    Require-DockerSuccess 'Local test image download'
}
$inspection = & docker image inspect $Image
Require-DockerSuccess 'Image lookup (use -PullImage if the image is not installed)'
$inspection | Set-Content -LiteralPath (Join-Path $resultDir 'image.json')
$imageInfo = ($inspection | ConvertFrom-Json)[0]
$pinnedImage = $imageInfo.Id
$server | Set-Content -LiteralPath (Join-Path $resultDir 'docker-server.json')
$volumeName = 'incidentforge-t0-' + [Guid]::NewGuid().ToString('N')
& docker volume create --label 'incidentforge.purpose=t0-evidence' $volumeName | Out-Null
Require-DockerSuccess 'Disposable evidence volume creation'
$containerId = $null

# Mount only source/test tools, NEVER planning docs, user credentials or Docker socket.
# Export reports after execution via docker cp; candidate UIDs get no host output mount.
try {
$dockerArgs = @('create', '--read-only', '--network', 'none', '--pids-limit', '128',
    '--memory', '512m', '--cpus', '2', '--cap-drop', 'ALL',
    '--cap-add', 'SETUID', '--cap-add', 'SETGID', '--cap-add', 'SETPCAP',
    '--cap-add', 'CHOWN', '--cap-add', 'KILL',
    '--security-opt', 'no-new-privileges=true',
    '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m,mode=1777',
    '--workdir', '/app', '--env', 'PYTHONDONTWRITEBYTECODE=1',
    '--mount', "type=volume,source=$volumeName,target=/evidence")
$mountDirectories = @('fixture','tests','probes')
if ($Stage -in @('t2','t6')) {
    $dockerArgs += @('--tmpfs', '/app:rw,nosuid,nodev,size=1m,mode=700')
    $mountDirectories += @('evaluation','contracts')
}
foreach ($directory in $mountDirectories) {
    $source = Join-Path $projectRoot $directory
    $dockerArgs += @('--mount', "type=bind,source=$source,target=/app/$directory,readonly")
}
$dockerArgs += @($pinnedImage, 'python', '-m', "probes.run_$Stage", '--require-linux', '--output', "/evidence/$Stage")
$containerId = (& docker @dockerArgs).Trim()
Require-DockerSuccess 'Container creation'
if ($containerId -notmatch '^[a-f0-9]{64}$') { throw 'Unexpected Docker container ID.' }
$containerId | Set-Content -LiteralPath (Join-Path $resultDir 'container-id.txt')
    & docker start $containerId | Out-Null
    Require-DockerSuccess 'Container start'
    $deadline = [DateTime]::UtcNow.AddSeconds(300)
    do {
        Start-Sleep -Seconds 1
        $running = & docker inspect --format '{{.State.Running}}' $containerId
        Require-DockerSuccess 'Container status'
        if ([DateTime]::UtcNow -ge $deadline) { throw "$Stage exceeded 300-second watchdog." }
    } while ($running -eq 'true')
    & docker logs $containerId 2>&1 | Set-Content -LiteralPath (Join-Path $resultDir 'container.log')
    & docker cp "${containerId}:/evidence/$Stage/." $resultDir
    Require-DockerSuccess 'Evidence export'
    $exitCode = & docker inspect --format '{{.State.ExitCode}}' $containerId
    & docker inspect $containerId | Set-Content -LiteralPath (Join-Path $resultDir 'container.json')
    if ($exitCode -ne '0') { throw "Linux acceptance failed (exit $exitCode). See $resultDir" }
    Write-Output "Linux $Stage passed. Evidence: $resultDir"
} finally {
    # Only remove the exact disposable container created above; never prune images/volumes.
    if ($containerId -match '^[a-f0-9]{64}$') {
        & docker rm --force $containerId | Out-Null
        Require-DockerSuccess 'Test container cleanup'
    }
    & docker volume rm $volumeName | Out-Null
    Require-DockerSuccess 'Disposable evidence volume cleanup'
}

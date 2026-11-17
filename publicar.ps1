# Compila e publica uma nova versao do A Tapioca no GitHub (release com .exe + SHA256SUMS).
# Normalmente voce nao roda este arquivo direto: de dois cliques em publicar.bat.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$repo = "Orthurus/a-tapioca"

function Parar($msg) { Write-Host ""; Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }

# 1) Compila (gera dist\A_Tapioca.exe e dist\SHA256SUMS)
try { & "$PSScriptRoot\compilar.ps1" } catch { Parar $_.Exception.Message }

$m = Select-String -Path "A_Tapioca.py" -Pattern '^VERSAO\s*=\s*"([^"]+)"'
$versao = $m.Matches[0].Groups[1].Value
$tag = "v$versao"
$exe = Join-Path $PSScriptRoot "dist\A_Tapioca.exe"
$sums = Join-Path $PSScriptRoot "dist\SHA256SUMS"
if (-not (Test-Path $exe) -or -not (Test-Path $sums)) { Parar "dist\A_Tapioca.exe ou dist\SHA256SUMS nao foram gerados." }

# 2) GitHub CLI (gh): instala se faltar
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando o GitHub CLI (gh) ..."
    winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Nao consegui instalar o gh. Abrindo a pagina de release para voce anexar os arquivos." -ForegroundColor Yellow
    Start-Process "https://github.com/$repo/releases/new?tag=$tag"
    Start-Process explorer.exe (Join-Path $PSScriptRoot "dist")
    exit 0
}

# 3) Login (so na primeira vez; voce autoriza no navegador)
cmd /c "gh auth status >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Faca login no GitHub (abre o navegador) ..."
    gh auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { Parar "Login no GitHub nao concluido." }
}

# 4) Nunca reutiliza tag
cmd /c "gh release view $tag --repo $repo >nul 2>&1"
if ($LASTEXITCODE -eq 0) { Parar "A release $tag ja existe no GitHub. Aumente VERSAO em A_Tapioca.py (ex.: proxima versao) e rode de novo." }

# 5) Notas da versao = secao do CHANGELOG.md, se existir
$notas = Join-Path $env:TEMP "notas_release.md"
$texto = "Versao $versao"
if (Test-Path "CHANGELOG.md") {
    $cl = Get-Content "CHANGELOG.md" -Raw -Encoding UTF8
    $r = [regex]::Match($cl, "(?ms)^##\s*\[?v?" + [regex]::Escape($versao) + "(?![\d.])\]?.*?\r?\n(.*?)(?=^##\s|\z)")
    if ($r.Success -and $r.Groups[1].Value.Trim()) { $texto = $r.Groups[1].Value.Trim() }
}
[System.IO.File]::WriteAllText($notas, $texto, (New-Object System.Text.UTF8Encoding $false))

# 6) Publica
Write-Host "Publicando $tag ..."
gh release create $tag $exe $sums --repo $repo --title "Versao $versao" --notes-file $notas --latest
if ($LASTEXITCODE -ne 0) { Parar "Falha ao criar a release." }

Write-Host ""
Write-Host "PUBLICADO: https://github.com/$repo/releases/tag/$tag" -ForegroundColor Green
Write-Host "Quem tem o programa aberto recebe o aviso de atualizacao."

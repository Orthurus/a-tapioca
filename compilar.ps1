# Compila o A Tapioca, gera o SHA256SUMS e mostra qual tag criar no GitHub.
# Uso (na pasta do projeto):  powershell -ExecutionPolicy Bypass -File .\compilar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$m = Select-String -Path "A_Tapioca.py" -Pattern '^VERSAO\s*=\s*"([^"]+)"'
if (-not $m) { throw "VERSAO nao encontrada em A_Tapioca.py" }
$versao = $m.Matches[0].Groups[1].Value

# Garante que o atualizador.py e a versao mais recente (evita compilar arquivo velho)
if (-not (Select-String -Path "atualizador.py" -Pattern "_contexto_certifi" -Quiet)) {
    throw "atualizador.py esta desatualizado. Substitua pelo mais recente antes de compilar."
}

Write-Host "Instalando dependencias ..."
pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias (certifi, tkcalendar, babel)." }

Write-Host "Compilando versao $versao ..."
$icone = @()
if (Test-Path "logo.ico") { $icone = @("--icon", "logo.ico") }
pyinstaller --onefile --windowed --noconfirm --clean --name A_Tapioca @icone --collect-all tkcalendar --collect-data certifi --hidden-import babel.numbers --hidden-import certifi A_Tapioca.py
if ($LASTEXITCODE -ne 0) { throw "O PyInstaller falhou." }

$dist = (Resolve-Path "dist").Path
$exe = Join-Path $dist "A_Tapioca.exe"
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
[System.IO.File]::WriteAllText((Join-Path $dist "SHA256SUMS"), "$hash  A_Tapioca.exe`n", (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "PRONTO. No GitHub, crie a release com a tag v$versao e anexe os dois arquivos:"
Write-Host "  $exe"
Write-Host "  $(Join-Path $dist 'SHA256SUMS')"
Write-Host ""
Write-Host "Dentro do programa a versao e $versao (tem que ser igual a tag)."

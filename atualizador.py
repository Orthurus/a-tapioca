"""Auto-atualização via GitHub Releases (reutilizável: DoNata, A Tapioca...).

Uso:
    info = checar("usuario/repositorio", "1.0")   # None se já está atualizado
    trocar_exe(info)                              # baixa, confere, troca e reinicia
    confirmar_inicio()                            # chamar no app, após a janela abrir

Requisitos da release no GitHub:
    - um asset .exe
    - um asset de checksum: "SHA256SUMS" (ou SHA256SUMS.txt / <nome>.exe.sha256),
      gerado com:  sha256sum MeuApp.exe > SHA256SUMS
      Sem checksum a atualização é RECUSADA.

Proteções: só roda no .exe empacotado; só baixa de hosts do GitHub (https, inclusive
nos redirecionamentos); confere tamanho, cabeçalho MZ e SHA-256; mantém o exe antigo
como .bak e faz rollback automático se o novo não confirmar que abriu.
"""
import hashlib, json, os, re, ssl, subprocess, sys, tempfile
import urllib.error, urllib.parse, urllib.request

API = "https://api.github.com"
HOSTS_PERMITIDOS = ("github.com", "githubusercontent.com")
TAMANHO_MAX = 500 * 1024 * 1024  # 500 MB


class ErroAtualizacao(Exception):
    """Erro com mensagem já pronta para mostrar ao usuário."""


# ----------------------------------------------------------------- versões
def vtuple(s):
    """'v1.0.0-beta' -> (1,). Zeros à direita são ignorados: 1.0 == 1.0.0."""
    base = str(s).strip().lstrip("vV").split("-")[0].split("+")[0]
    t = [int(x) for x in re.findall(r"\d+", base)] or [0]
    while len(t) > 1 and t[-1] == 0:
        t.pop()
    return tuple(t)


# ------------------------------------------------------------------- rede
def _host_ok(url):
    p = urllib.parse.urlparse(url)
    h = (p.hostname or "").lower()
    return p.scheme == "https" and any(h == d or h.endswith("." + d) for d in HOSTS_PERMITIDOS)


class _Redirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _host_ok(newurl):
            raise ErroAtualizacao("Redirecionamento para um endereço não permitido; download cancelado.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(ctx=None):
    handlers = [_Redirecionamento()]
    if ctx is not None:
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def _contexto_certifi():
    """Contexto TLS com os certificados raiz do pacote 'certifi' (levado dentro do .exe).
    Serve de reserva quando o repositório de certificados do Windows está incompleto."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _abrir(url, timeout=15):
    """A verificação do certificado do servidor NUNCA é desligada."""
    if not _host_ok(url):
        raise ErroAtualizacao("Endereço de download não permitido (só https do GitHub).")
    req = urllib.request.Request(url, headers={"User-Agent": "atualizador"})
    try:
        return _opener().open(req, timeout=timeout)
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            ctx = _contexto_certifi()
            if ctx is not None:
                return _opener(ctx).open(req, timeout=timeout)
        raise


def _traduzir(e):
    if isinstance(e, ErroAtualizacao):
        return e
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (403, 429):
            return ErroAtualizacao("O GitHub limitou as consultas por enquanto. Tente de novo mais tarde.")
        return ErroAtualizacao(f"O GitHub respondeu com erro {e.code}.")
    if isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
        return ErroAtualizacao("Este computador não conseguiu validar o certificado de segurança do GitHub.\n"
                               "Confira a data e a hora do Windows, rode o Windows Update e veja se o antivírus "
                               "não está interceptando conexões HTTPS.")
    if isinstance(e, (urllib.error.URLError, OSError)):
        return ErroAtualizacao("Sem conexão com o GitHub. Verifique a internet.")
    return ErroAtualizacao(f"Resposta inesperada do GitHub: {e}")


def checar(repo, versao_atual, api=API):
    """Devolve {'versao','exe','exe_nome','tamanho','sha256_url','apk'} se houver versão
    mais nova; senão None. Levanta ErroAtualizacao (mensagem amigável) em falhas."""
    try:
        with _abrir(f"{api}/repos/{repo}/releases/latest") as r:
            rel = json.load(r)
        if rel.get("draft") or rel.get("prerelease"):
            return None
        versao = str(rel["tag_name"]).lstrip("vV")
        if vtuple(versao) <= vtuple(versao_atual):
            return None
        assets = rel.get("assets", [])
    except urllib.error.HTTPError as e:
        if e.code == 404:  # ainda não existe nenhuma versão publicada
            return None
        raise _traduzir(e)
    except (ErroAtualizacao, KeyError, ValueError, TypeError, OSError) as e:
        raise _traduzir(e)

    def achar(pred):
        return next((a for a in assets if pred(a["name"].lower())), None)

    exe = achar(lambda n: n.endswith(".exe"))
    apk = achar(lambda n: n.endswith(".apk"))
    sha = None
    if exe:
        n_exe = exe["name"].lower()
        sha = achar(lambda n: n in ("sha256sums", "sha256sums.txt", "checksums.txt", n_exe + ".sha256"))
    return {
        "versao": versao,
        "exe": exe["browser_download_url"] if exe else None,
        "exe_nome": exe["name"] if exe else None,
        "tamanho": exe.get("size") if exe else None,
        "sha256_url": sha["browser_download_url"] if sha else None,
        "apk": apk["browser_download_url"] if apk else None,
    }


def baixar(url, destino):
    tmp = destino + ".tmp"
    try:
        with _abrir(url, timeout=60) as r, open(tmp, "wb") as f:
            total = 0
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                total += len(b)
                if total > TAMANHO_MAX:
                    raise ErroAtualizacao("Arquivo maior que o esperado; download cancelado.")
                f.write(b)
            f.flush()
            os.fsync(f.fileno())
            esperado = r.headers.get("Content-Length")
        if esperado and esperado.isdigit() and total != int(esperado):
            raise ErroAtualizacao(f"Download interrompido (recebidos {total} de {esperado} bytes).")
        os.replace(tmp, destino)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise _traduzir(e)


# --------------------------------------------------------------- integridade
def _sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _decodificar(b):
    """Aceita UTF-8, UTF-8 com BOM e UTF-16 (o PowerShell 5 grava '>' em UTF-16)."""
    if b.startswith(b"\xef\xbb\xbf"):
        return b.decode("utf-8-sig", "replace")
    if b.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in b:
        return b.decode("utf-16", "replace")
    return b.decode("utf-8", "replace")


def _norm(nome):
    # o GitHub troca espaços/símbolos no nome dos assets (A Tapioca.exe -> A.Tapioca.exe)
    return re.sub(r"[^a-z0-9]", "", os.path.basename(nome.strip()).lower())


def _sha256_esperado(url, nome_exe):
    try:
        with _abrir(url, timeout=15) as r:
            texto = _decodificar(r.read(65536))
    except Exception as e:
        raise _traduzir(e)
    achados = [(h.lower(), (n or "").strip())
               for h, n in re.findall(r"(?im)^\s*([0-9a-f]{64})\s*(?:\*|\s)\s*(\S.*?)?\s*$", texto)]
    if not achados:
        raise ErroAtualizacao("O arquivo de checksum está vazio ou em formato inválido "
                              "(esperado: <hash de 64 caracteres>  <nome do .exe>).")
    for h, n in achados:
        if n and (n.lower() == nome_exe.lower() or _norm(n) == _norm(nome_exe)):
            return h
    # Um único hash no arquivo: aceita mesmo com nome diferente. Não perde segurança: o hash é
    # conferido contra o arquivo realmente baixado.
    if len({h for h, _ in achados}) == 1:
        return achados[0][0]
    nomes = ", ".join(n or "(sem nome)" for _, n in achados)
    raise ErroAtualizacao(f"O checksum da release não lista o executável.\nEsperado: {nome_exe}\nNo arquivo: {nomes}")


def _conferir(novo, esperado_sha, tamanho):
    """O SHA-256 é o critério de integridade. O tamanho publicado só ajuda a explicar a falha."""
    tam = os.path.getsize(novo)
    with open(novo, "rb") as f:
        if f.read(2) != b"MZ":
            raise ErroAtualizacao(f"O arquivo baixado ({tam} bytes) não é um executável do Windows válido.")
    if _sha256_arquivo(novo) != esperado_sha:
        extra = f" Baixado: {tam} bytes; publicado: {tamanho} bytes." if tamanho and tam != tamanho else ""
        raise ErroAtualizacao("Falha na verificação de integridade (SHA-256): o .exe da release não corresponde "
                              "ao SHA256SUMS." + extra)


# ------------------------------------------------------------------- troca
def marcador(atual=None):
    atual = atual or sys.executable
    return os.path.join(tempfile.gettempdir(), os.path.basename(atual) + ".update_ok")


def confirmar_inicio():
    """O app chama isto depois de abrir. Se ele foi iniciado pela atualização, avisa o
    .bat de que o exe novo funciona (sem isso, o .bat restaura o exe antigo)."""
    if os.environ.get("ATUALIZANDO") != "1":
        return
    try:
        with open(marcador(), "w") as f:
            f.write("ok")
    except OSError:
        pass
    os.environ.pop("ATUALIZANDO", None)


def _bat_esc(p):
    return p.replace("%", "%%")


LOG = os.path.join(tempfile.gettempdir(), "atualizador_log.txt")
ESPERA_1S = "ping -n 2 127.0.0.1 >nul"   # 'timeout' falha sem console; ping funciona sempre
ESPERA_2S = "ping -n 3 127.0.0.1 >nul"


def gerar_bat(atual, novo, pasta=None, marc=None, espera_confirmacao=30):
    """Troca atual por novo (guardando .bak), abre o novo e faz rollback se ele não
    confirmar o início. `%` nos caminhos é escapado; o resto fica entre aspas.
    Cada etapa é registrada em LOG (atualizador_log.txt, na pasta temporária)."""
    bak = atual + ".bak"
    marc = marc or marcador(atual)
    A, N, B, M, L = (_bat_esc(x) for x in (atual, novo, bak, marc, LOG))
    P = _bat_esc(pasta or os.path.dirname(atual))
    nome = _bat_esc(os.path.basename(atual))
    log = lambda msg: f'echo %date% %time% {msg} >> "{L}"\n'
    return (
        "@echo off\nchcp 65001 >nul\nset n=0\n"
        + log("bat iniciado") +
        f":t\nset /a n+=1\n{ESPERA_1S}\n"
        f'move /y "{A}" "{B}" >nul 2>&1\n'
        "if errorlevel 1 if %n% lss 30 goto t\n"
        "if errorlevel 1 goto falha\n"
        + log("exe antigo guardado como .bak") +
        f'move /y "{N}" "{A}" >nul 2>&1\n'
        "if errorlevel 1 goto rollback\n"
        + log("exe novo no lugar; abrindo") +
        f'del "{M}" >nul 2>&1\n'
        f'set ATUALIZANDO=1\nstart "" /d "{P}" "{A}"\nset ATUALIZANDO=\n'
        f"set n=0\n:w\n{ESPERA_1S}\n"
        f'if exist "{M}" goto ok\n'
        f"set /a n+=1\nif %n% lss {espera_confirmacao} goto w\n"
        + log("novo exe NAO confirmou inicio; voltando ao antigo") +
        f'taskkill /f /im "{nome}" >nul 2>&1\n{ESPERA_2S}\n'
        f'del /f "{A}" >nul 2>&1\n'
        f':rollback\nmove /y "{B}" "{A}" >nul 2>&1\n'
        f':falha\n' + log("rollback/falha: reabrindo versao anterior") +
        f'del "{N}" >nul 2>&1\n'
        f'start "" /d "{P}" "{A}"\ngoto fim\n'
        f':ok\n' + log("atualizacao confirmada") +
        f'del "{B}" >nul 2>&1\ndel "{M}" >nul 2>&1\n'
        ':fim\n(goto) 2>nul & del "%~f0"\n'
    )


def trocar_exe(info):
    """Baixa, confere e troca o .exe, reabrindo o programa. Recebe o dict de checar()."""
    if not getattr(sys, "frozen", False):
        raise ErroAtualizacao("A atualização automática só funciona no programa instalado (.exe).")
    if not sys.platform.startswith("win"):
        raise ErroAtualizacao("A atualização automática só está disponível no Windows.")
    if not isinstance(info, dict) or not info.get("exe"):
        raise ErroAtualizacao("A versão publicada não tem um arquivo .exe.")
    if not info.get("sha256_url"):
        raise ErroAtualizacao("A versão publicada não tem arquivo SHA256SUMS; atualização recusada por segurança.")

    atual = sys.executable
    pasta = os.path.dirname(atual)
    if not os.access(pasta, os.W_OK):
        raise ErroAtualizacao(f"Sem permissão para gravar em:\n{pasta}\nMova o programa para uma pasta sua (ex.: Documentos).")

    esperado = _sha256_esperado(info["sha256_url"], info.get("exe_nome") or os.path.basename(info["exe"]))
    novo = atual + ".novo"
    try:
        baixar(info["exe"], novo)
    except ErroAtualizacao:
        baixar(info["exe"], novo)   # uma nova tentativa (queda de conexão, download cortado)
    try:
        _conferir(novo, esperado, info.get("tamanho"))
    except Exception:
        try:
            os.remove(novo)
        except OSError:
            pass
        raise

    fd, bat = tempfile.mkstemp(prefix="atualizar_", suffix=".bat")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(gerar_bat(atual, novo, pasta))
    env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    # CREATE_NO_WINDOW (console oculto, herdado pelos comandos do .bat: nada de janelas piscando).
    # Não usar DETACHED_PROCESS: sem console, cada comando abre uma janela e 'timeout' falha.
    subprocess.Popen(["cmd", "/c", bat], env=env, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=0x08000000)

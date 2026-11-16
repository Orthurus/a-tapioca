# Histórico de versões

## 1.1.3
- Atualizador: usa os certificados do `certifi` (embutidos no `.exe`) quando o Windows não consegue validar o certificado do GitHub. A verificação do certificado nunca é desligada.
- Mensagem de erro clara para falha de certificado.
- `compilar.ps1` instala as dependências e inclui o `certifi` no executável.

## 1.1.2
- Só uma verificação/atualização por vez (corrige janelas duplicadas).
- Atualizador: leitura tolerante do `SHA256SUMS` (UTF-8/UTF-16, nomes renomeados pelo GitHub); o SHA-256 passou a ser o critério de integridade; detecção de download cortado com uma nova tentativa.
- `.bat` de atualização sem `timeout` (falha sem console) e com log em `%TEMP%\atualizador_log.txt`.

## 1.1.1
- Vendas novas guardam o preço unitário da época (`linhas`), além de `id` e `mesa`.
- Confirmação antes de limpar o pedido.

## 1.1
- Dados em `%APPDATA%\ATapioca`, gravação atômica com `.bak` e aviso de arquivo corrompido.
- Pedidos abertos (mesas/comandas) salvos e restaurados.
- Atualização automática com verificação de SHA-256 e rollback.

## 1.0
- Versão inicial.

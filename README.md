# A Tapioca — Sistema de Vendas

Sistema de caixa (PDV) para tapiocaria, feito em Python com Tkinter. Roda no Windows, funciona sem internet e é distribuído como um único `.exe`, com atualização automática pelo GitHub.

## Funcionalidades

- **Pedido (Caixa):** vários pedidos ao mesmo tempo, em mesas ou comandas. Cada mesa tem seu próprio carrinho, e é possível adicionar, aumentar, diminuir e remover itens. Os pedidos abertos são salvos a cada alteração e voltam se o programa for fechado ou o computador reiniciar.
- **Cardápio / Estoque:** cadastro, edição e remoção de produtos, com preço e categoria (Salgadas, Doces, Bebidas, Combos, Outros).
- **Relatório de Vendas:** faturamento por dia, resumo dos itens mais vendidos e histórico das vendas do dia, com navegação entre datas.
- **Cupom:** gera um arquivo de texto e envia para a impressora padrão do Windows (bobina de 22 colunas). A impressão pode ser desligada. Também há impressão de *conferência*, que mostra o pedido sem finalizar a venda.
- **Atualização automática:** verifica novas versões no GitHub ao abrir, confere a integridade do arquivo e faz rollback se a nova versão não abrir.

## Requisitos

| Uso | O que precisa |
|---|---|
| Só usar o programa | Windows e o `A_Tapioca.exe` |
| Rodar pelo código | Python 3.10 ou mais novo, com Tkinter (já vem no instalador do Python) |
| Seletor de datas no relatório | `pip install tkcalendar` (opcional) |
| Gerar o `.exe` | `pip install pyinstaller tkcalendar babel` |

## Rodando pelo código

```
python A_Tapioca.py
```

Pelo código, a atualização automática fica desativada. Ela só funciona no `.exe`.

## Onde ficam os dados

Os dados ficam em `%APPDATA%\ATapioca`, fora da pasta do programa. Por isso trocar ou atualizar o `.exe` nunca mexe neles.

| Arquivo | Conteúdo |
|---|---|
| `cardapio.json` | Produtos, preços e categorias |
| `vendas.json` | Histórico de vendas |
| `pedidos.json` | Mesas e comandas ainda abertas |
| `config.json` | Preferências (por exemplo, imprimir o cupom) |
| `*.bak` | Cópia do último arquivo íntegro de cada um acima |
| `cupons\` | Cupons e conferências em texto |

**Como os dados são protegidos**

- Toda gravação é atômica: o programa grava num arquivo temporário, confere e só então troca o arquivo definitivo.
- Se um arquivo estiver danificado, o programa guarda uma cópia dele (`.corrompido-DATA`), restaura o `.bak` e avisa o que aconteceu.
- Se uma venda não puder ser gravada, o pedido continua aberto e nada é perdido.
- Na primeira execução, se houver `cardapio.json`, `vendas.json` ou `config.json` ao lado do programa (versões antigas), eles são **copiados** para a pasta nova. Os originais não são apagados.

**Backup:** copie a pasta `%APPDATA%\ATapioca` de vez em quando para um pendrive ou nuvem. É tudo o que o programa precisa para ser restaurado.

### Formato de uma venda

```json
{
  "id": "20261028213000-a1b2c3",
  "data": "28/10/2026",
  "hora": "21:30:00",
  "mesa": "Mesa 1",
  "itens": { "Tapioca de Manteiga": 2 },
  "linhas": [
    { "nome": "Tapioca de Manteiga", "qtd": 2, "preco_unit": 10.0, "subtotal": 20.0 }
  ],
  "total": 20.0
}
```

As `linhas` guardam o preço da época, então mudar o cardápio depois não altera o histórico. Vendas anteriores à versão 1.1.1 têm só `itens` (quantidades) e `total`.

## Atualização automática

O programa consulta a última release do repositório configurado em `REPO_ATUALIZACAO`, no topo do `A_Tapioca.py`. Se a versão publicada for maior que a `VERSAO` do código, ele oferece atualizar.

Antes de trocar o executável, o `atualizador.py`:

1. Aceita apenas downloads por `https` de endereços do GitHub, inclusive nos redirecionamentos.
2. Exige um arquivo `SHA256SUMS` na release e **recusa a atualização sem ele**.
3. Confere o cabeçalho do arquivo e o SHA-256 do `.exe` baixado.
4. Guarda o `.exe` atual como `.bak`, troca o arquivo e reabre o programa.
5. Se a versão nova não confirmar que abriu em cerca de 30 segundos, restaura a anterior.

Os passos da troca ficam registrados em `%TEMP%\atualizador_log.txt`.

> A atualização exige permissão de escrita na pasta do `.exe`. Em `C:\Program Files`, por exemplo, ela falha. Mantenha o programa numa pasta do usuário.

## Publicando uma nova versão

1. Altere `VERSAO` no `A_Tapioca.py` (por exemplo, `"1.2"`).
2. Na pasta do projeto, rode:
   ```
   powershell -ExecutionPolicy Bypass -File .\compilar.ps1
   ```
   O script compila o `.exe`, gera o `SHA256SUMS` e mostra a tag que deve ser usada.
3. No GitHub, crie uma release com a tag **`v` + versão** (por exemplo, `v1.2`) e anexe `dist\A_Tapioca.exe` e `dist\SHA256SUMS`.

**Regras importantes**

- A tag da release precisa ser igual ao `VERSAO` que está **dentro** do `.exe`. Se forem diferentes, o programa se atualiza para a mesma versão em loop.
- Nunca reaproveite uma tag já publicada. Para corrigir algo, publique uma versão nova.
- Se recompilar o `.exe`, gere o `SHA256SUMS` de novo, porque o hash muda a cada build.
- Um `.exe` já instalado só se atualiza sozinho se tiver o `atualizador.py` correto. Em caso de dúvida, instale o `.exe` novo manualmente uma vez.

O comando de compilação que o script executa é:

```
pyinstaller --onefile --windowed --noconfirm --clean --name A_Tapioca --collect-all tkcalendar --hidden-import babel.numbers A_Tapioca.py
```

## Estrutura do projeto

```
A Tapioca/
├── A_Tapioca.py      # aplicação (interface, pedidos, cardápio, relatório, persistência)
├── atualizador.py    # atualização automática via GitHub Releases
├── compilar.ps1      # compila, gera SHA256SUMS e indica a tag
└── dist/             # saída do build (A_Tapioca.exe e SHA256SUMS)
```

## Solução de problemas

| Mensagem ou sintoma | O que fazer |
|---|---|
| "A versão publicada não tem arquivo SHA256SUMS" | Anexe o `SHA256SUMS` à release (edite a release e envie o arquivo). |
| "Falha na verificação de integridade" | O `.exe` da release não é o mesmo usado para gerar o `SHA256SUMS`. Gere o hash de novo a partir do `.exe` publicado. |
| O programa oferece a mesma atualização toda vez | A `VERSAO` dentro do `.exe` é menor que a tag da release. Recompile com a versão certa. |
| "Sem permissão para gravar" | Mova o programa para uma pasta sua, como Documentos. |
| A atualização não aconteceu | Veja `%TEMP%\atualizador_log.txt`. |
| Aviso de dados restaurados ao abrir | Um arquivo estava danificado. Foi restaurado do `.bak`, e a cópia ruim ficou em `%APPDATA%\ATapioca`. |

## Limitações conhecidas

- O cupom **não é um documento fiscal**.
- O programa **não registra a forma de pagamento**, nem valor recebido ou troco.
- Não há controle de estoque (o "Estoque" do menu é o cadastro de produtos).
- Os dados ficam em arquivos JSON, sem controle de acesso por usuário.

## Próximos passos

- Registro de pagamentos (forma, valor recebido e troco).
- Migração dos dados para SQLite, com histórico mais rastreável.
- Testes automatizados e separação do código em módulos.

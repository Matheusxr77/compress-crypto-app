# CryptoCompress

Aplicação Flask para extração de texto, criptografia localizada por palavra-chave,
compressão lossless, reversão e análise de desempenho em arquivos `.txt`, `.pdf` e
`.docx`.

## Funcionalidades

- Criptografia Fernet somente dos blocos/frases que contêm palavras-chave.
- Dez codecs com interface comum: Huffman, Arithmetic, BWT, Golomb, LZ77, LZMA,
  LZW, PAQ, PPM e RLE.
- Execução concorrente com a opção **Todos**.
- Inspeção do texto extraído, texto cifrado e hexdump dos pacotes.
- Descompactação, descriptografia e reconstrução de TXT, PDF e DOCX.
- Métricas CSV para extração, criptografia, compressão, descompactação e
  descriptografia.
- Benchmark por algoritmo-arquivo com tamanho original/comprimido, razão e
  fator de compressão, space saving, bpc, throughputs de
  compressão/descompressão, assimetria temporal, memória pico, ganho líquido,
  risco de expansão e validação lossless.
- Dashboard com tabela e gráfico Chart.js.

## Apresentação do App

Use este roteiro para demonstrar o fluxo completo do aplicativo:

1. **Apresentação:** explique que o CryptoCompress extrai texto, criptografa
   palavras-chave, compara codecs lossless e permite reverter os arquivos.
2. **Processamento:** na aba **Processar**, selecione um `.txt`, `.pdf` ou
   `.docx`, escolha um algoritmo ou **Todos** e, opcionalmente, informe
   palavras-chave como `CPF` ou `confidencial`.
3. **Resultado e chave:** mostre o identificador do documento, os blocos
   localizados e a chave Fernet. Explique que a chave não é armazenada e deve
   ser guardada para a reversão.
4. **Inspeção:** abra a aba **Inspecionar** para visualizar o texto extraído,
   o texto com criptografia localizada e o início dos pacotes comprimidos.
5. **Comparação:** no dashboard de **Métricas**, compare tamanho original,
   criptografado e comprimido, além de razão, economia, tempo e memória por
   algoritmo.
6. **Simulador:** informe um volume e alterne entre GB e TB no simulador para
   estimar armazenamento, custo mensal e economia.
7. **Reversão:** na aba **Reverter**, selecione o documento e o método, informe
   a chave quando necessário e valide o texto recuperado. Em seguida, baixe o
   arquivo reconstruído ou o ZIP com todos os métodos.
8. **Limpeza:** encerre a demonstração usando **Limpar arquivos armazenados**
   no dashboard para remover os artefatos e zerar as métricas.

## Execução local

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "chave-local-de-desenvolvimento"
python app.py
```

Abra `http://localhost:5000`.

O diretório `storage/` é criado automaticamente e contém:

```text
storage/
├── uploads/
├── encrypted/
├── compressed/
├── restored/
└── metrics/
```

Cada linha de benchmark em `storage/metrics/metrics.csv` representa um método
de compressão aplicado ao arquivo. `original_bytes` é o tamanho dos bytes que
entram no codec (após a criptografia localizada), e `compressed_bytes` é o
tamanho do pacote produzido. A validação lossless compara os bytes
descompactados com os bytes de entrada usando igualdade exata.

Também são registrados `original_file_bytes`, `encrypted_file_bytes`,
`compressed_file_bytes`, além das razões `ratio_original_compressed` e
`ratio_encrypted_compressed`.
Também são calculados separadamente `space_saving_original_percent`
(Original→Comprimido) e `space_saving_encrypted_percent`
(Criptografado→Comprimido).
O simulador de armazenamento do dashboard usa custo mensal em dólar (USD) por GB.

## Deploy no Render

### Opção 1: Blueprint

1. Publique o projeto em um repositório GitHub.
2. No Render, escolha **New > Blueprint**.
3. Selecione o repositório e confirme o arquivo `render.yaml`.
4. O Render instalará `requirements.txt` e iniciará `gunicorn app:app`.
5. A variável `SECRET_KEY` será gerada automaticamente pelo Blueprint.

### Opção 2: Web Service manual

Configure:

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Health Check Path | `/` |

Adicione uma variável de ambiente `SECRET_KEY` forte e aleatória.

### Persistência no Render

O plano padrão do Render possui filesystem efêmero. Portanto, arquivos enviados
e métricas CSV podem ser apagados após um deploy ou reinicialização. Para
produção, configure um Persistent Disk montado em `/var/data` e use essa pasta
nas variáveis de armazenamento, ou substitua o repositório CSV por PostgreSQL e
um storage de objetos.

## Segurança

- Não versionar chaves, arquivos enviados ou a pasta `storage/`.
- Em produção, sempre definir `SECRET_KEY`.
- A chave Fernet não é persistida pelo sistema; o usuário precisa guardá-la
  para executar a reversão.
- Os CPFs e demais dados usados nos testes devem ser fictícios.

## Estrutura

```text
app.py                  # application factory e inicialização
config.py               # configurações e pastas
core/                   # extractors, crypto, codecs, pipeline e métricas
routes/                 # Blueprints Flask
templates/              # interface Jinja2
static/                 # CSS e recursos visuais
render.yaml             # Blueprint de deploy no Render
```

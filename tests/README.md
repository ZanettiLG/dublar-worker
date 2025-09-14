# Testes Unitários - Dublar Worker

Este diretório contém os testes unitários para o projeto dublar-worker, focando especificamente no módulo `deps`.

## Estrutura

```
tests/
├── conftest.py              # Fixtures e configurações comuns
├── deps/                    # Testes para o módulo deps
│   ├── test_dep_base.py     # Testes para DepBase
│   ├── test_spleeter.py     # Testes para Spleeter
│   ├── test_media.py        # Testes para Media
│   ├── test_transformers.py # Testes para Transformers
│   └── test_transcriber.py  # Testes para Transcriber
└── README.md               # Este arquivo
```

## Configuração

### Instalação das Dependências

```bash
# Instalar todas as dependências (incluindo pytest)
pip install -e .

# Ou usando uv (se disponível)
uv sync
```

**Nota:** O pytest e suas dependências já estão incluídas nas dependências principais do projeto, não sendo necessário instalação separada.

### Configuração do Pytest

O pytest está configurado no `pyproject.toml` com as seguintes opções:

- **Cobertura**: `--cov=deps` - Gera relatório de cobertura para o módulo deps
- **Relatórios**: `--cov-report=term-missing` e `--cov-report=html:htmlcov`
- **Marcadores**: `unit`, `integration`, `slow`

## Executando os Testes

### Todos os Testes

```bash
pytest
```

### Testes por Módulo

```bash
# Apenas testes do DepBase
pytest tests/deps/test_dep_base.py

# Apenas testes do Spleeter
pytest tests/deps/test_spleeter.py

# Apenas testes do Media
pytest tests/deps/test_media.py

# Apenas testes do Transformers
pytest tests/deps/test_transformers.py

# Apenas testes do Transcriber
pytest tests/deps/test_transcriber.py
```

### Testes por Marcador

```bash
# Apenas testes unitários
pytest -m unit

# Apenas testes de integração
pytest -m integration

# Excluir testes lentos
pytest -m "not slow"
```

### Com Cobertura

```bash
# Executar com relatório de cobertura
pytest --cov=deps --cov-report=html

# O relatório HTML será gerado em htmlcov/index.html
```

### Modo Verboso

```bash
# Executar com saída verbosa
pytest -v

# Executar com saída muito verbosa
pytest -vv
```

## Fixtures Disponíveis

### Fixtures de Sistema
- `temp_dir`: Diretório temporário para testes
- `sample_audio_file`: Arquivo de áudio de exemplo
- `sample_media_url`: URL de exemplo para download
- `sample_headers`: Headers HTTP de exemplo

### Fixtures de Mock
- `mock_worker`: Mock da classe Worker
- `mock_separator`: Mock do Separator do Spleeter
- `mock_httpx_client`: Mock do AsyncClient do httpx
- `mock_logger`: Mock do logger
- `mock_torch`: Mock do torch
- `mock_tensorflow`: Mock do TensorFlow

### Fixtures de Configuração
- `progress_callback`: Callback de progresso para testes
- `event_loop`: Event loop para testes assíncronos

## Cobertura de Testes

Os testes cobrem:

### DepBase
- ✅ Inicialização com engine customizada e padrão
- ✅ Chamada do método load na inicialização
- ✅ Implementação padrão do método load
- ✅ Atributos name e engine
- ✅ Herança da classe

### Spleeter
- ✅ Inicialização e configuração do TensorFlow
- ✅ Método load com configuração do Separator
- ✅ Execução bem-sucedida de separação
- ✅ Tratamento de erros (arquivos não criados)
- ✅ Criação de diretórios de saída
- ✅ Extração de nome do arquivo
- ✅ Construção de caminhos de saída
- ✅ Configuração de GPU (quando disponível)

### Media
- ✅ Inicialização e configuração do AsyncClient
- ✅ Download assíncrono com e sem headers/progresso
- ✅ Tratamento de erros durante download
- ✅ Métodos síncronos e bloqueantes
- ✅ Obtenção de informações de mídia
- ✅ Inicialização automática do cliente
- ✅ Callback de progresso

### Transformers
- ✅ Inicialização com modelo e task
- ✅ Método load com pipeline
- ✅ Herança de DepBase
- ✅ Configuração de device_map
- ✅ Diferentes modelos e tarefas

### Transcriber
- ✅ Inicialização com modelos Whisper
- ✅ Dicionário de modelos disponíveis
- ✅ Herança de Transformers
- ✅ Task automatic-speech-recognition
- ✅ Método execute com timestamps
- ✅ Diferentes modelos Whisper
- ✅ Inferência de device

## Marcadores de Teste

- `@pytest.mark.unit`: Testes unitários rápidos
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.slow`: Testes que demoram para executar
- `@pytest.mark.asyncio`: Testes assíncronos

## Notas

- Os testes usam mocks extensivamente para isolar as unidades sob teste
- Testes assíncronos são marcados com `@pytest.mark.asyncio`
- Fixtures são reutilizáveis entre diferentes arquivos de teste
- Cobertura de código é gerada automaticamente para o módulo `deps`

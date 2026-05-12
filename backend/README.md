# Backend Mães Mobilizadoras

## Configuração

Primeiramente, instale *uv*, uma alternativa ao gerenciador de pacotes padrão *pip*, disponível em https://docs.astral.sh/uv/getting-started/installation/. Então, navegue ao diretório do backend, crie um *virtualenv* e instale as dependências do projeto:

```bash
cd backend
uv venv --python 3.14 .venv
source .venv/bin/activate  # (ou .\venv\Scripts\activate no Windows)
```

## Execução

No diretório do backend, ative o *virtualenv* se não estiver ativo e, então, execute a ferramenta *flask*.
```bash
cd backend
source .venv/bin/activate  # (ou .\venv\Scripts\activate no Windows)
python -m flask run
```

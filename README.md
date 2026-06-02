# Arranjo de Oradores

Aplicação Django para cadastrar discursos públicos e controlar notificações automáticas ao orador 30, 15, 7 e 2 dias antes da data do discurso.

## Stack

- Python
- Django
- SQLite
- Django Admin
- Jazzmin
- APScheduler
- Integração futura com Z-API para WhatsApp

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## Execução

```powershell
python manage.py runserver
```

Acesse o painel administrativo em:

```text
http://127.0.0.1:8000/admin/
```

## Verificação de notificações

Para processar manualmente as notificações pendentes:

```powershell
python manage.py processar_notificacoes
```

Para listar o que seria enviado sem disparar mensagens:

```powershell
python manage.py processar_notificacoes --dry-run
```

Para processar apenas uma mensagem, útil para teste real com Z-API:

```powershell
python manage.py processar_notificacoes --limite 1
```

Para processar uma notificação específica:

```powershell
python manage.py processar_notificacoes --notificacao-id 8
```

Também é possível enviar pelo Django Admin:

1. Acesse `Notificações`.
2. Selecione uma ou mais notificações.
3. Escolha a ação `Enviar/reprocessar notificações selecionadas`.
4. Clique em `Executar`.

Para retestar uma notificação com erro, selecione-a e use primeiro `Marcar selecionadas como pendente`, depois execute o envio.

Para iniciar o agendador diário com APScheduler:

```powershell
python manage.py iniciar_agendador --hora 08:00
```

## Comportamento das notificações

- Ao salvar um discurso agendado ou confirmado, o sistema cria notificações para 30, 15, 7 e 2 dias antes.
- A combinação de discurso e marco é única, evitando duplicidade.
- Notificações pendentes são identificadas por `Notificacao.objects.pendentes()`.
- O envio de WhatsApp é simulado em `discursos/services.py`, sem chamada real à Z-API.
- O histórico fica registrado no próprio modelo `Notificacao`, com `data_envio`, `status_envio` e `resposta_api`.

## Endereço das congregações

O cadastro de congregações possui campos de endereço:

- CEP
- logradouro
- número
- complemento
- bairro
- cidade
- estado

Ao cadastrar ou editar uma congregação no Django Admin, informe o CEP e salve. Se o logradouro ainda estiver vazio, o sistema consulta o ViaCEP em `https://viacep.com.br/ws/{CEP}/json/` e preenche endereço, bairro, cidade e estado automaticamente. Número e complemento continuam manuais.

O endereço cadastrado é incluído automaticamente nas mensagens de WhatsApp.

## Integração com Z-API

Por padrão, o sistema continua usando envio simulado. Para habilitar a Z-API real, copie o arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` com os dados reais:

```env
ZAPI_ENABLED=True
ZAPI_BASE_URL=https://api.z-api.io
ZAPI_INSTANCE_ID=sua_instancia
ZAPI_INSTANCE_TOKEN=seu_token_da_instancia
ZAPI_CLIENT_TOKEN=seu_client_token
ZAPI_TIMEOUT_SECONDS=15
ZAPI_WEBHOOK_SECRET=um-segredo-para-webhooks
```

Depois reinicie o servidor ou o agendador.

`ZAPI_BASE_URL` deve ficar preferencialmente como `https://api.z-api.io`. Se você colar a URL completa do endpoint de envio, o sistema também aceita, mas manter só o domínio evita confusão.

A integração usa o endpoint de texto simples da Z-API:

```text
POST /instances/{instanceId}/token/{token}/send-text
```

O sistema envia:

```json
{
  "phone": "5511999999999",
  "message": "Mensagem de lembrete"
}
```

As credenciais ficam somente em variáveis de ambiente e não devem ser versionadas. O arquivo `.env` já está ignorado pelo Git.

## Webhooks da Z-API

O sistema possui dois endpoints para a Z-API:

```text
/webhooks/zapi/recebidas/
/webhooks/zapi/status/
```

Em produção na Railway, configure na tela de webhooks da Z-API:

```text
Ao receber:
https://arranjo-de-oradores-production.up.railway.app/webhooks/zapi/recebidas/?token=SEU_ZAPI_WEBHOOK_SECRET

Receber status da mensagem:
https://arranjo-de-oradores-production.up.railway.app/webhooks/zapi/status/?token=SEU_ZAPI_WEBHOOK_SECRET
```

Use o mesmo valor de `ZAPI_WEBHOOK_SECRET` configurado nas variáveis da Railway. Esse token simples impede que qualquer pessoa publique dados nos webhooks apenas conhecendo a URL.

As respostas recebidas ficam em `Respostas de notificações` no Django Admin. Os eventos de entrega/leitura ficam em `Eventos de status das mensagens`.

## Deploy na Railway

O projeto já inclui `railway.json` para deploy com Nixpacks.

Antes de subir, crie um projeto na Railway com:

- um serviço para a aplicação Django;
- um banco PostgreSQL;
- variáveis de ambiente no serviço Django.

Variáveis recomendadas:

```env
DJANGO_SECRET_KEY=uma-chave-secreta-grande-e-segura
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://*.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
ZAPI_ENABLED=True
ZAPI_BASE_URL=https://api.z-api.io
ZAPI_INSTANCE_ID=sua_instancia
ZAPI_INSTANCE_TOKEN=seu_token_da_instancia
ZAPI_CLIENT_TOKEN=seu_client_token
ZAPI_TIMEOUT_SECONDS=15
```

O build executa:

```bash
python manage.py collectstatic --noinput
```

O start command executa:

```bash
python manage.py migrate && gunicorn arranjo_oradores.wsgi:application --bind 0.0.0.0:$PORT
```

A Railway fornece a variável `$PORT`; por isso o servidor precisa escutar em `0.0.0.0:$PORT`.

### Disparo automático diário na Railway

O serviço web roda o Django Admin e recebe webhooks. Para executar verificações diárias automaticamente, crie um segundo serviço na Railway como **Cron Job**, usando o mesmo repositório e as mesmas variáveis de ambiente do serviço web.

Configure esse segundo serviço assim:

```text
Start Command:
python manage.py processar_notificacoes

Cron Schedule:
0 11 * * *
```

Esse exemplo roda todos os dias às 11:00 UTC, que corresponde a 08:00 em America/Sao_Paulo.

Não use `python manage.py iniciar_agendador` na Railway. O APScheduler é útil para execução local ou para um worker contínuo, mas a Railway recomenda cron jobs que executam uma tarefa curta e terminam. O comando `processar_notificacoes` faz exatamente isso: verifica as notificações pendentes, envia o que for devido e encerra o processo.

O serviço Cron Job deve usar:

- o mesmo `DATABASE_URL` do PostgreSQL;
- as mesmas variáveis da Z-API;
- `DJANGO_DEBUG=False`;
- sem domínio público, pois ele não recebe HTTP.

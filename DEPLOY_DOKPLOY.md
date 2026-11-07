# Guia de Deploy no Dokploy e Exemplos `curl` (`http://instaloader.cleissoncardoso.com`)

Este guia descreve como publicar a API do Instagram (Instaloader + FastAPI) no **Dokploy** utilizando o domínio **`http://instaloader.cleissoncardoso.com`** e lista todos os comandos `curl` prontos para uso.

---

## 1. Como Instalar e Configurar no Dokploy

O repositório já possui [`Dockerfile`](Dockerfile), [`.dockerignore`](.dockerignore) e [`requirements.txt`](requirements.txt) configurados na raiz.

### Passo 1: Criar a Aplicação no Dokploy
1. Acesse o painel do seu **Dokploy**.
2. Entre no seu **Project** (ou crie um novo projeto, ex: `instagram-scraper`).
3. Clique em **Create Service** -> **Application**.
4. Defina um nome (ex: `instaloader-api`) e clique em **Create**.

### Passo 2: Conectar o Repositório GitHub
1. Na aba **General** da aplicação, em **Source Type**, selecione **GitHub** (ou **Git** caso use URL pública).
2. Selecione o repositório: `CleissonCardoso2025/instaloader`
   - **Branch**: `master` (ou `main`, conforme a branch padrão do repositório)
   - **Build Path**: `/`
3. Em **Build Type**, selecione **Dockerfile**:
   - **Dockerfile Path**: `Dockerfile`
   - **Docker Context Path**: `.`
4. Clique em **Save**.

### Passo 3: Configurar o Domínio (`instaloader.cleissoncardoso.com`)
1. No seu provedor de DNS (Cloudflare, Registro.br, Hostinger, etc.), crie um registro apontando para o IP da sua VPS onde roda o Dokploy:
   - **Tipo**: `A`
   - **Nome / Host**: `instaloader`
   - **Valor / IPv4**: `IP_DA_SUA_VPS`
2. No painel do Dokploy, abra a aba **Domains** da aplicação e clique em **Add Domain**:
   - **Host**: `instaloader.cleissoncardoso.com`
   - **Path**: `/`
   - **Container Port**: `8000`
   - **HTTPS**: Desmarque se for utilizar apenas `http://instaloader.cleissoncardoso.com`, ou ative **HTTPS (Let's Encrypt)** caso queira também responder em `https://`.
3. Clique em **Create** / **Save**.

### Passo 4: (Opcional) Volume Persistente para Downloads
Caso utilize os endpoints `/api/v1/downloads/...` e queira manter os arquivos salvos mesmo após novos deploys:
1. Vá na aba **Mounts / Volumes** -> **Add Mount**.
2. **Type**: `Volume`
3. **Volume Name**: `instaloader-downloads`
4. **Mount Path (Container)**: `/app/downloads`

### Passo 5: Fazer o Deploy
1. Volte para a aba **General** e clique em **Deploy**.
2. Acompanhe a aba **Logs** até aparecer:
   `Uvicorn running on http://0.0.0.0:8000`
3. Acesse a documentação interativa no navegador:
   - **Swagger UI**: `http://instaloader.cleissoncardoso.com/docs`
   - **ReDoc**: `http://instaloader.cleissoncardoso.com/redoc`

---

## 2. Exemplos de `curl` para Todos os Endpoints

### Status da API (Health Check)
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/health" \
  -H "accept: application/json"
```

---

### Perfis (`Profiles`)

#### 1. Dados completos de um perfil pelo `@username`
Retorna biografia, hashtags/menções na bio, contagem de seguidores, seguindo, total de posts, foto de perfil HD, categoria comercial e links externos:
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram" \
  -H "accept: application/json"
```

#### 2. Dados de um perfil pelo ID numérico
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/id/25025320" \
  -H "accept: application/json"
```

#### 3. Listar posts recentes de um perfil
Parâmetros opcionais: `limit` (padrão `12`, máx `100`), `only_videos` (`true`/`false`), `only_pictures` (`true`/`false`), `include_sidecar` (`true`/`false`):
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/posts?limit=6&only_videos=false&only_pictures=false&include_sidecar=true" \
  -H "accept: application/json"
```

#### 4. Listar Reels de um perfil
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/reels?limit=6" \
  -H "accept: application/json"
```

#### 5. Listar posts em que o perfil foi marcado (`Tagged`)
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/tagged?limit=6" \
  -H "accept: application/json"
```

#### 6. Listar vídeos IGTV de um perfil
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/igtv?limit=6" \
  -H "accept: application/json"
```

#### 7. Listar Stories ativos de um perfil
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/stories" \
  -H "accept: application/json"
```

#### 8. Listar Destaques (`Highlights`) de um perfil
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/highlights?include_items=true" \
  -H "accept: application/json"
```

#### 9. Listar Seguidores (`Followers`) e Seguindo (`Followees`)
```bash
# Seguidores
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/followers?limit=20" \
  -H "accept: application/json"

# Seguindo
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/followees?limit=20" \
  -H "accept: application/json"
```

#### 10. Listar contas similares sugeridas
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/profiles/instagram/similar?limit=10" \
  -H "accept: application/json"
```

---

### Posts & Reels Individuais

#### 1. Obter detalhes completos de um Post ou Reel pelo `shortcode`
Retorna legenda, hashtags, menções, curtidas, contagem de comentários, visualizações/plays de vídeo, URL do vídeo `.mp4`, URL da imagem e todos os slides do carrossel (`sidecar_nodes`):
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/posts/C1234567890" \
  -H "accept: application/json"
```

#### 2. Obter detalhes de um Post ou Reel pela URL completa (via `POST`)
Funciona com links `/p/...`, `/reel/...`, `/reels/...` ou `/tv/...`:
```bash
curl -X POST "http://instaloader.cleissoncardoso.com/api/v1/posts/by-url" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/C1234567890/"
  }'
```

#### 3. Obter detalhes de um Post ou Reel pela URL completa (via `GET`)
```bash
curl -G "http://instaloader.cleissoncardoso.com/api/v1/posts/by-url" \
  --data-urlencode "url=https://www.instagram.com/p/C1234567890/" \
  -H "accept: application/json"
```

#### 4. Obter Post pelo `mediaid` numérico
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/posts/mediaid/3261234567890123456" \
  -H "accept: application/json"
```

#### 5. Converter entre `shortcode` e `mediaid`
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/posts/convert/C1234567890" \
  -H "accept: application/json"
```

#### 6. Listar comentários e respostas de um Post
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/posts/C1234567890/comments?limit=30&max_answers=5" \
  -H "accept: application/json"
```

#### 7. Listar perfis que curtiram um Post
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/posts/C1234567890/likes?limit=30" \
  -H "accept: application/json"
```

---

### Hashtags & Busca (`Search`)

#### 1. Informações de uma Hashtag
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/hashtags/python" \
  -H "accept: application/json"
```

#### 2. Top Posts e Posts Recentes de uma Hashtag
```bash
curl -X GET "http://instaloader.cleissoncardoso.com/api/v1/hashtags/python/posts?limit=10&include_top=true&include_recent=true" \
  -H "accept: application/json"
```

#### 3. Busca Geral no Instagram (Perfis, Hashtags e Localizações)
```bash
curl -G "http://instaloader.cleissoncardoso.com/api/v1/search" \
  --data-urlencode "q=tecnologia" \
  --data-urlencode "limit=15" \
  -H "accept: application/json"
```

---

### Downloads de Mídia & Proxy Direto

#### 1. Baixar todas as mídias de um Post no servidor
Retorna a lista de arquivos salvos e as URLs estáticas (`http://instaloader.cleissoncardoso.com/downloads/...`):
```bash
curl -X POST "http://instaloader.cleissoncardoso.com/api/v1/downloads/post/C1234567890" \
  -H "accept: application/json"
```

#### 2. Baixar foto de perfil e últimos posts de um perfil no servidor
```bash
curl -X POST "http://instaloader.cleissoncardoso.com/api/v1/downloads/profile/instagram?limit=4&include_profile_pic=true" \
  -H "accept: application/json"
```

#### 3. Proxy direto para baixar/exibir imagem ou vídeo do CDN do Instagram
Útil para evitar bloqueio de CORS no frontend ou baixar o arquivo direto (`download=true`):
```bash
curl -G "http://instaloader.cleissoncardoso.com/api/v1/downloads/proxy" \
  --data-urlencode "url=URL_DA_IMAGEM_OU_VIDEO_DO_INSTAGRAM" \
  --data-urlencode "download=true" \
  -o midia_baixada.mp4
```

---

### Sessão Opcional (Caso queira autenticar com Cookies para rotas restritas)

Por padrão a API roda em **modo 100% público (sem login)**. Caso deseje habilitar rotas que o próprio Instagram bloqueia sem sessão (como stories privados ou lista completa de seguidores):

```bash
# Carregar cookies de sessão
curl -X POST "http://instaloader.cleissoncardoso.com/api/v1/session/cookies" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "seu_usuario",
    "cookies": {
      "sessionid": "SEU_SESSION_ID",
      "csrftoken": "SEU_CSRF_TOKEN",
      "ds_user_id": "SEU_USER_ID",
      "mid": "SEU_MID",
      "ig_did": "SEU_IG_DID"
    }
  }'

# Resetar de volta para o modo 100% público/anônimo
curl -X POST "http://instaloader.cleissoncardoso.com/api/v1/session/reset" \
  -H "accept: application/json"
```

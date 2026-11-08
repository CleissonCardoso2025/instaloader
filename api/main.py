"""Aplicação FastAPI principal com todos os endpoints para scraping do Instagram via Instaloader."""

from typing import List

from fastapi import FastAPI, HTTPException, Path, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import instaloader
from instaloader.exceptions import InstaloaderException
from instaloader.structures import Post

from .schemas import (
    CommentSchema,
    DownloadResponse,
    FollowersDiffResponse,
    HashtagPostsResponse,
    HashtagSchema,
    HealthResponse,
    HighlightSchema,
    LoginRequest,
    PostByUrlRequest,
    PostSchema,
    ProfileDetailSchema,
    ProfileSummarySchema,
    SearchResultsSchema,
    SessionCookiesRequest,
    StorySchema,
)
from .service import InstagramScraperService, extract_shortcode

app = FastAPI(
    title="Instagram Scraper API (Instaloader)",
    description=(
        "API REST completa para scraping de dados públicos do Instagram "
        "construída sobre o **Instaloader**.\n\n"
        "### Principais Recursos:\n"
        "- **Perfis**: Biografia, seguidores, seguindo, categoria, foto HD, "
        "posts, reels, IGTV e marcados.\n"
        "- **Posts & Reels**: Consulta por `shortcode`, `mediaid` ou link direto "
        "do Instagram (incluindo carrossel/sidecar, vídeos e comentários).\n"
        "- **Hashtags & Busca**: Top posts, posts recentes por hashtag e busca "
        "geral (`TopSearchResults`).\n"
        "- **Downloads & Proxy**: Salvar mídias no servidor ou fazer "
        "streaming/download direto contornando bloqueios de CORS.\n"
        "- **Modo Público por Padrão**: Funciona sem login para dados públicos, "
        "com suporte opcional a sessão/cookies para rotas restritas."
    ),
    version=instaloader.__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper_service = InstagramScraperService(download_dir="downloads")

app.mount(
    "/downloads",
    StaticFiles(directory=str(scraper_service.download_dir)),
    name="downloads",
)


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redireciona a raiz para a documentação interativa Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Status & Sessão"],
    summary="Verifica o status da API e do Instaloader",
)
def health_check():
    return scraper_service.get_status()


# =============================================================================
# 1. PERFIS (PROFILES)
# =============================================================================
@app.get(
    "/api/v1/profiles/{username}",
    response_model=ProfileDetailSchema,
    tags=["Perfis"],
    summary="Obter dados completos de um perfil pelo username",
)
def get_profile(
    username: str = Path(..., description="Username do perfil do Instagram (sem @)"),
):
    return scraper_service.get_profile(username)


@app.get(
    "/api/v1/profiles/id/{profile_id}",
    response_model=ProfileDetailSchema,
    tags=["Perfis"],
    summary="Obter dados de um perfil pelo ID numérico",
)
def get_profile_by_id(
    profile_id: int = Path(..., description="ID numérico do usuário no Instagram"),
):
    return scraper_service.get_profile_by_id(profile_id)


@app.get(
    "/api/v1/profiles/{username}/posts",
    response_model=List[PostSchema],
    tags=["Perfis"],
    summary="Listar publicações (posts) de um perfil",
)
def get_profile_posts(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        12, ge=1, le=100, description="Quantidade máxima de posts a retornar"
    ),
    only_videos: bool = Query(False, description="Retornar apenas vídeos"),
    only_pictures: bool = Query(False, description="Retornar apenas fotos"),
    include_sidecar: bool = Query(
        True, description="Incluir todos os itens internos de carrosséis (sidecar)"
    ),
):
    return scraper_service.get_profile_posts(
        username=username,
        limit=limit,
        only_videos=only_videos,
        only_pictures=only_pictures,
        include_sidecar=include_sidecar,
    )


@app.get(
    "/api/v1/profiles/{username}/reels",
    response_model=List[PostSchema],
    tags=["Perfis"],
    summary="Listar Reels de um perfil",
)
def get_profile_reels(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        12, ge=1, le=100, description="Quantidade máxima de reels a retornar"
    ),
):
    return scraper_service.get_profile_reels(username=username, limit=limit)


@app.get(
    "/api/v1/profiles/{username}/tagged",
    response_model=List[PostSchema],
    tags=["Perfis"],
    summary="Listar posts em que o perfil foi marcado",
)
def get_profile_tagged(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        12, ge=1, le=100, description="Quantidade máxima de posts marcados"
    ),
):
    return scraper_service.get_profile_tagged_posts(username=username, limit=limit)


@app.get(
    "/api/v1/profiles/{username}/igtv",
    response_model=List[PostSchema],
    tags=["Perfis"],
    summary="Listar vídeos de IGTV de um perfil",
)
def get_profile_igtv(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        12, ge=1, le=100, description="Quantidade máxima de vídeos IGTV"
    ),
):
    return scraper_service.get_profile_igtv(username=username, limit=limit)


@app.get(
    "/api/v1/profiles/{username}/stories",
    response_model=List[StorySchema],
    tags=["Perfis"],
    summary="Listar Stories ativos de um perfil",
)
def get_profile_stories(
    username: str = Path(..., description="Username do perfil"),
):
    return scraper_service.get_profile_stories(username=username)


@app.get(
    "/api/v1/profiles/{username}/highlights",
    response_model=List[HighlightSchema],
    tags=["Perfis"],
    summary="Listar Destaques (Highlights) de um perfil",
)
def get_profile_highlights(
    username: str = Path(..., description="Username do perfil"),
    include_items: bool = Query(
        True, description="Carregar todos os itens de mídia de cada destaque"
    ),
):
    return scraper_service.get_profile_highlights(
        username=username, include_items=include_items
    )


@app.get(
    "/api/v1/profiles/{username}/followers",
    response_model=List[ProfileSummarySchema],
    tags=["Perfis"],
    summary="Listar seguidores de um perfil",
)
def get_profile_followers(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(50, ge=1, le=500, description="Quantidade máxima de seguidores"),
):
    return scraper_service.get_profile_followers(username=username, limit=limit)


@app.get(
    "/api/v1/profiles/{username}/new-followers",
    response_model=FollowersDiffResponse,
    tags=["Perfis"],
    summary=(
        "Identificar novos seguidores desde o último GET (quantos entraram e quem são)"
    ),
)
def get_profile_new_followers(
    username: str = Path(..., description="Username do perfil do Instagram (sem @)"),
    max_scan: int = Query(
        200,
        ge=10,
        le=2000,
        description=(
            "Quantidade máxima de seguidores recentes a escanear para identificar "
            "quem são os novos seguidores (quando autenticado com IG_SESSIONID)"
        ),
    ),
    reset_snapshot: bool = Query(
        False,
        description=(
            "Se True, descarta o histórico anterior e cria um novo snapshot base agora"
        ),
    ),
):
    return scraper_service.check_new_followers(
        username=username,
        max_scan=max_scan,
        reset_snapshot=reset_snapshot,
    )


@app.get(
    "/api/v1/profiles/{username}/followees",
    response_model=List[ProfileSummarySchema],
    tags=["Perfis"],
    summary="Listar perfis seguidos (followees) por um perfil",
)
def get_profile_followees(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        50, ge=1, le=500, description="Quantidade máxima de perfis seguidos"
    ),
):
    return scraper_service.get_profile_followees(username=username, limit=limit)


@app.get(
    "/api/v1/profiles/{username}/similar",
    response_model=List[ProfileSummarySchema],
    tags=["Perfis"],
    summary="Listar contas similares/sugeridas para um perfil",
)
def get_profile_similar(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        20, ge=1, le=100, description="Quantidade máxima de contas similares"
    ),
):
    return scraper_service.get_profile_similar_accounts(username=username, limit=limit)


# =============================================================================
# 2. POSTS & REELS INDIVIDUAIS
# =============================================================================
@app.get(
    "/api/v1/posts/by-url",
    response_model=PostSchema,
    tags=["Posts & Reels"],
    summary="Obter detalhes de um post ou reel a partir da URL completa do Instagram",
)
def get_post_by_url_query(
    url: str = Query(
        ...,
        description="URL do post ou reel no Instagram (ex: https://www.instagram.com/p/SHORTCODE/)",
    ),
):
    return scraper_service.get_post_by_shortcode(url)


@app.post(
    "/api/v1/posts/by-url",
    response_model=PostSchema,
    tags=["Posts & Reels"],
    summary="Obter detalhes de um post ou reel enviando a URL no corpo (JSON)",
)
def get_post_by_url_body(payload: PostByUrlRequest):
    return scraper_service.get_post_by_shortcode(payload.url)


@app.get(
    "/api/v1/posts/mediaid/{mediaid}",
    response_model=PostSchema,
    tags=["Posts & Reels"],
    summary="Obter detalhes de um post pelo Media ID numérico",
)
def get_post_by_mediaid(
    mediaid: int = Path(..., description="Media ID numérico do post"),
):
    return scraper_service.get_post_by_mediaid(mediaid)


@app.get(
    "/api/v1/posts/convert/{shortcode_or_mediaid}",
    tags=["Posts & Reels"],
    summary="Converter entre Shortcode e Media ID numérico",
)
def convert_shortcode_mediaid(
    shortcode_or_mediaid: str = Path(
        ..., description="Shortcode alfanumérico ou Media ID numérico"
    ),
):
    try:
        if shortcode_or_mediaid.isdigit():
            mediaid = int(shortcode_or_mediaid)
            shortcode = Post.mediaid_to_shortcode(mediaid)
        else:
            shortcode = extract_shortcode(shortcode_or_mediaid)
            mediaid = Post.shortcode_to_mediaid(shortcode)
        return {
            "shortcode": shortcode,
            "mediaid": mediaid,
            "instagram_url": f"https://www.instagram.com/p/{shortcode}/",
        }
    except (InstaloaderException, HTTPException, ValueError) as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/v1/posts/{shortcode}",
    response_model=PostSchema,
    tags=["Posts & Reels"],
    summary="Obter detalhes completos de um post ou reel pelo Shortcode",
)
def get_post(
    shortcode: str = Path(..., description="Shortcode do post/reel (ex: C1234567890)"),
):
    return scraper_service.get_post_by_shortcode(shortcode)


@app.get(
    "/api/v1/posts/{shortcode}/comments",
    response_model=List[CommentSchema],
    tags=["Posts & Reels"],
    summary="Listar comentários e respostas de um post",
)
def get_post_comments(
    shortcode: str = Path(..., description="Shortcode do post"),
    limit: int = Query(
        50, ge=1, le=500, description="Quantidade máxima de comentários principais"
    ),
    max_answers: int = Query(
        10, ge=0, le=100, description="Quantidade máxima de respostas por comentário"
    ),
):
    return scraper_service.get_post_comments(
        shortcode, limit=limit, max_answers=max_answers
    )


@app.get(
    "/api/v1/posts/{shortcode}/likes",
    response_model=List[ProfileSummarySchema],
    tags=["Posts & Reels"],
    summary="Listar perfis que curtiram um post",
)
def get_post_likes(
    shortcode: str = Path(..., description="Shortcode do post"),
    limit: int = Query(50, ge=1, le=500, description="Quantidade máxima de perfis"),
):
    return scraper_service.get_post_likes(shortcode, limit=limit)


# =============================================================================
# 3. HASHTAGS & BUSCA (SEARCH)
# =============================================================================
@app.get(
    "/api/v1/hashtags/{hashtag}",
    response_model=HashtagSchema,
    tags=["Hashtags & Busca"],
    summary="Obter metadados de uma Hashtag",
)
def get_hashtag_info(
    hashtag: str = Path(..., description="Nome da hashtag (sem #)"),
):
    return scraper_service.get_hashtag_info(hashtag)


@app.get(
    "/api/v1/hashtags/{hashtag}/posts",
    response_model=HashtagPostsResponse,
    tags=["Hashtags & Busca"],
    summary="Obter Top Posts e Posts Recentes de uma Hashtag",
)
def get_hashtag_posts(
    hashtag: str = Path(..., description="Nome da hashtag (sem #)"),
    limit: int = Query(
        12, ge=1, le=100, description="Limite de posts a retornar por seção"
    ),
    include_top: bool = Query(True, description="Incluir os Top Posts da hashtag"),
    include_recent: bool = Query(
        True, description="Incluir os Posts mais recentes da hashtag"
    ),
):
    return scraper_service.get_hashtag_posts(
        tag_name=hashtag,
        limit=limit,
        include_top=include_top,
        include_recent=include_recent,
    )


@app.get(
    "/api/v1/search",
    response_model=SearchResultsSchema,
    tags=["Hashtags & Busca"],
    summary="Busca geral no Instagram (Perfis, Hashtags e Localizações)",
)
def search_instagram(
    q: str = Query(..., min_length=1, description="Termo de pesquisa"),
    limit: int = Query(
        20, ge=1, le=100, description="Limite de resultados por categoria"
    ),
):
    return scraper_service.search_instagram(query=q, limit=limit)


# =============================================================================
# 4. DOWNLOAD DE ARQUIVOS & PROXY DE MÍDIA
# =============================================================================
@app.post(
    "/api/v1/downloads/post/{shortcode}",
    response_model=DownloadResponse,
    tags=["Downloads & Mídia"],
    summary="Baixar fotos, vídeos, legenda e metadados de um post para o servidor",
)
def download_post(
    shortcode: str = Path(..., description="Shortcode do post"),
):
    return scraper_service.download_post_to_server(shortcode)


@app.post(
    "/api/v1/downloads/profile/{username}",
    response_model=DownloadResponse,
    tags=["Downloads & Mídia"],
    summary="Baixar foto de perfil e posts recentes de um perfil para o servidor",
)
def download_profile(
    username: str = Path(..., description="Username do perfil"),
    limit: int = Query(
        6,
        ge=0,
        le=50,
        description="Quantidade de posts recentes para baixar (0 = apenas foto de perfil)",
    ),
    include_profile_pic: bool = Query(
        True, description="Baixar também a foto de perfil"
    ),
):
    return scraper_service.download_profile_to_server(
        username=username,
        limit=limit,
        include_profile_pic=include_profile_pic,
    )


@app.get(
    "/api/v1/downloads/proxy",
    tags=["Downloads & Mídia"],
    summary="Proxy direto para visualizar ou baixar qualquer URL de mídia do Instagram",
)
def proxy_media(
    url: str = Query(
        ..., description="URL direta da imagem ou vídeo retornado nos endpoints da API"
    ),
    download: bool = Query(
        False,
        description="Se True, força o download do arquivo no navegador",
    ),
):
    content, content_type, filename = scraper_service.fetch_media_stream(url)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(content=content, media_type=content_type, headers=headers)


# =============================================================================
# 5. SESSÃO OPCIONAL (MODO PÚBLICO POR PADRÃO + SUPORTE A COOKIES SE NECESSÁRIO)
# =============================================================================
@app.post(
    "/api/v1/session/cookies",
    tags=["Status & Sessão"],
    summary="(Opcional) Carregar cookies de sessão do navegador para rotas restritas",
)
def load_session_cookies(payload: SessionCookiesRequest):
    return scraper_service.set_session_cookies(payload.username, payload.cookies)


@app.post(
    "/api/v1/session/login",
    tags=["Status & Sessão"],
    summary="(Opcional) Autenticar com usuário e senha",
)
def login_session(payload: LoginRequest):
    return scraper_service.login_with_credentials(payload.username, payload.password)


@app.post(
    "/api/v1/session/reset",
    tags=["Status & Sessão"],
    summary="Voltar para o modo 100% público/anônimo (remove qualquer sessão ativa)",
)
def reset_session():
    return scraper_service.reset_to_public_session()

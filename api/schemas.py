"""Modelos Pydantic (schemas) para requisição e resposta da API do Instagram."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Status da API")
    instaloader_version: str = Field(..., description="Versão do Instaloader")
    is_logged_in: bool = Field(...,
                               description="Se há sessão autenticada ativa")
    logged_username: Optional[str] = Field(
        None, description="Usuário autenticado (se houver)"
    )


class LocationSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    has_public_page: Optional[bool] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class SidecarNodeSchema(BaseModel):
    index: int = Field(..., description="Índice do item no carrossel (base 1)")
    is_video: bool = Field(...,
                           description="Se este item do carrossel é um vídeo")
    display_url: str = Field(...,
                             description="URL da imagem ou miniatura do vídeo")
    video_url: Optional[str] = Field(
        None, description="URL direta do vídeo (se for vídeo)"
    )


class ProfileSummarySchema(BaseModel):
    userid: Optional[int] = Field(
        None, description="ID numérico do perfil no Instagram"
    )
    username: str = Field(..., description="Nome de usuário (@username)")
    full_name: Optional[str] = Field(
        None, description="Nome completo exibido no perfil"
    )
    is_private: Optional[bool] = Field(
        None, description="Se o perfil é privado")
    is_verified: Optional[bool] = Field(
        None, description="Se o perfil é verificado")
    profile_pic_url: Optional[str] = Field(
        None, description="URL da foto de perfil")


class ProfileDetailSchema(ProfileSummarySchema):
    biography: Optional[str] = Field(None, description="Biografia do perfil")
    biography_hashtags: List[str] = Field(
        default_factory=list, description="Hashtags presentes na bio"
    )
    biography_mentions: List[str] = Field(
        default_factory=list, description="Menções (@) presentes na bio"
    )
    external_url: Optional[str] = Field(
        None, description="Link externo na bio")
    bio_links: List[Dict[str, Any]] = Field(
        default_factory=list, description="Lista de links na bio"
    )
    followers: Optional[int] = Field(None, description="Número de seguidores")
    followees: Optional[int] = Field(
        None, description="Número de perfis seguidos")
    mediacount: Optional[int] = Field(None, description="Total de publicações")
    igtvcount: Optional[int] = Field(None, description="Total de vídeos IGTV")
    is_business_account: Optional[bool] = Field(
        None, description="Se é uma conta comercial/profissional"
    )
    business_category_name: Optional[str] = Field(
        None, description="Categoria da conta comercial"
    )
    instagram_url: str = Field(...,
                               description="URL pública do perfil no Instagram")


class PostSchema(BaseModel):
    shortcode: str = Field(..., description="Shortcode único do post/reel")
    mediaid: int = Field(..., description="ID numérico da mídia")
    instagram_url: str = Field(...,
                               description="Link direto para o post no Instagram")
    typename: str = Field(
        ..., description="Tipo da mídia: GraphImage, GraphVideo ou GraphSidecar"
    )
    date_utc: datetime = Field(...,
                               description="Data/hora da publicação em UTC")
    date_local: datetime = Field(
        ..., description="Data/hora da publicação no fuso local"
    )
    owner_username: Optional[str] = Field(
        None, description="Username do autor do post")
    owner_id: Optional[int] = Field(None, description="ID do autor do post")
    title: Optional[str] = Field(
        None, description="Título do post (quando aplicável)")
    caption: Optional[str] = Field(
        None, description="Legenda completa do post")
    caption_hashtags: List[str] = Field(
        default_factory=list, description="Hashtags na legenda"
    )
    caption_mentions: List[str] = Field(
        default_factory=list, description="Menções (@) na legenda"
    )
    accessibility_caption: Optional[str] = Field(
        None, description="Texto alternativo de acessibilidade"
    )
    tagged_users: List[str] = Field(
        default_factory=list, description="Usuários marcados na publicação"
    )
    is_video: bool = Field(...,
                           description="Se a publicação principal é um vídeo/reel")
    url: str = Field(...,
                     description="URL da imagem principal ou thumbnail do vídeo")
    video_url: Optional[str] = Field(
        None, description="URL direta do arquivo de vídeo (.mp4)"
    )
    video_duration: Optional[float] = Field(
        None, description="Duração do vídeo em segundos"
    )
    video_view_count: Optional[int] = Field(
        None, description="Contagem de visualizações do vídeo"
    )
    video_play_count: Optional[int] = Field(
        None, description="Contagem de reproduções (plays) do Reel/vídeo"
    )
    likes: Optional[int] = Field(None, description="Quantidade de curtidas")
    comments_count: Optional[int] = Field(
        None, description="Quantidade total de comentários"
    )
    mediacount: int = Field(
        1,
        description="Quantidade de itens (1 para foto/vídeo único, >1 para carrossel)",
    )
    is_sponsored: bool = Field(
        False, description="Se é publicação patrocinada")
    sponsor_users: List[str] = Field(
        default_factory=list, description="Perfis patrocinadores"
    )
    location: Optional[LocationSchema] = Field(
        None, description="Localização marcada no post"
    )
    sidecar_nodes: List[SidecarNodeSchema] = Field(
        default_factory=list,
        description="Itens individuais quando typename == GraphSidecar (carrossel)",
    )


class CommentAnswerSchema(BaseModel):
    id: int
    created_at_utc: datetime
    text: str
    owner_username: str
    owner_id: Optional[int] = None
    likes_count: int = 0


class CommentSchema(BaseModel):
    id: int
    created_at_utc: datetime
    text: str
    owner_username: str
    owner_id: Optional[int] = None
    likes_count: int = 0
    answers: List[CommentAnswerSchema] = Field(default_factory=list)


class StoryItemSchema(BaseModel):
    mediaid: int
    shortcode: str
    typename: Optional[str] = None
    date_utc: datetime
    expiring_utc: Optional[datetime] = None
    is_video: bool
    url: str
    video_url: Optional[str] = None
    caption: Optional[str] = None
    caption_hashtags: List[str] = Field(default_factory=list)
    caption_mentions: List[str] = Field(default_factory=list)
    owner_username: Optional[str] = None
    owner_id: Optional[int] = None


class StorySchema(BaseModel):
    owner_username: str
    owner_id: int
    latest_media_utc: Optional[datetime] = None
    itemcount: int
    items: List[StoryItemSchema] = Field(default_factory=list)


class HighlightSchema(BaseModel):
    unique_id: int
    title: str
    owner_username: str
    owner_id: int
    cover_url: Optional[str] = None
    cover_cropped_url: Optional[str] = None
    itemcount: int
    items: List[StoryItemSchema] = Field(default_factory=list)


class HashtagSchema(BaseModel):
    name: str
    hashtagid: Optional[int] = None
    mediacount: Optional[int] = None
    description: Optional[str] = None
    profile_pic_url: Optional[str] = None
    allow_following: Optional[bool] = None
    instagram_url: str


class HashtagPostsResponse(BaseModel):
    hashtag: HashtagSchema
    top_posts: List[PostSchema] = Field(default_factory=list)
    recent_posts: List[PostSchema] = Field(default_factory=list)


class SearchResultsSchema(BaseModel):
    query: str
    profiles: List[ProfileSummarySchema] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    locations: List[LocationSchema] = Field(default_factory=list)


class PostByUrlRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL completa do post, reel ou IGTV do Instagram",
        examples=["https://www.instagram.com/p/C123456/"],
    )


class DownloadResponse(BaseModel):
    target: str = Field(...,
                        description="Alvo do download (shortcode ou username)")
    directory: str = Field(
        ..., description="Caminho do diretório onde os arquivos foram salvos"
    )
    files: List[str] = Field(
        default_factory=list, description="Lista de arquivos baixados"
    )
    static_urls: List[str] = Field(
        default_factory=list,
        description="URLs locais para baixar/visualizar os arquivos",
    )


class SessionCookiesRequest(BaseModel):
    username: str = Field(
        ..., description="Username da conta correspondente aos cookies"
    )
    cookies: Dict[str, str] = Field(
        ...,
        description="Dicionário de cookies do navegador (ex: sessionid, csrftoken, ds_user_id)",
    )


class LoginRequest(BaseModel):
    username: str = Field(..., description="Usuário do Instagram")
    password: str = Field(..., description="Senha do Instagram")


class FollowersDiffResponse(BaseModel):
    username: str = Field(..., description="Username do perfil monitorado")
    is_first_snapshot: bool = Field(
        ...,
        description="True na primeira chamada (cria o snapshot inicial); False nas chamadas seguintes",
    )
    previous_snapshot_at: Optional[datetime] = Field(
        None, description="Data/hora (UTC) da consulta anterior"
    )
    current_snapshot_at: datetime = Field(
        ..., description="Data/hora (UTC) da consulta atual"
    )
    elapsed_seconds: Optional[float] = Field(
        None, description="Segundos decorridos desde a última consulta"
    )
    previous_followers_count: Optional[int] = Field(
        None, description="Total de seguidores na consulta anterior"
    )
    current_followers_count: int = Field(
        ..., description="Total de seguidores na consulta atual"
    )
    followers_count_delta: int = Field(
        0,
        description="Saldo líquido de seguidores no intervalo (current - previous)",
    )
    new_followers_count: int = Field(
        0, description="Quantidade de novos seguidores identificados no intervalo"
    )
    new_followers: List[ProfileSummarySchema] = Field(
        default_factory=list,
        description="Lista nominal de quem são os novos seguidores (requer sessão/cookies ativos)",
    )
    lost_followers_count: int = Field(
        0, description="Quantidade de seguidores que saíram no intervalo"
    )
    lost_followers: List[ProfileSummarySchema] = Field(
        default_factory=list,
        description="Lista nominal de quem deixou de seguir (quando disponível)",
    )
    who_tracking_available: bool = Field(
        False,
        description="True se a API está autenticada (IG_SESSIONID) e conseguiu listar quem são os seguidores",
    )
    message: str = Field(..., description="Resumo em português do monitoramento")

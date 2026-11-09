"""Camada de serviço que gerencia o Instaloader e executa as operações de scraping."""

from contextlib import suppress
import json
import os
import re
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import unquote, urlparse

from fastapi import HTTPException

import instaloader
from instaloader import (
    AbortDownloadException,
    BadCredentialsException,
    BadResponseException,
    ConnectionException,
    Hashtag,
    Instaloader,
    InstaloaderException,
    InvalidArgumentException,
    LoginException,
    LoginRequiredException,
    Post,
    PrivateProfileNotFollowedException,
    Profile,
    ProfileNotExistsException,
    QueryReturnedBadRequestException,
    QueryReturnedForbiddenException,
    QueryReturnedNotFoundException,
    TooManyRequestsException,
    TopSearchResults,
    TwoFactorAuthRequiredException,
)

from .schemas import (
    CommentSchema,
    DownloadResponse,
    FollowersDiffResponse,
    HashtagPostsResponse,
    HashtagSchema,
    HighlightSchema,
    PostSchema,
    ProfileDetailSchema,
    ProfileSummarySchema,
    SearchResultsSchema,
    StorySchema,
)
from .serializers import (
    serialize_comment,
    serialize_hashtag,
    serialize_highlight,
    serialize_location,
    serialize_post,
    serialize_profile_detail,
    serialize_profile_summary,
    serialize_story,
)

SHORTCODE_URL_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)"
)

HANDLED_EXCEPTIONS = (
    InstaloaderException,
    AbortDownloadException,
    HTTPException,
    KeyError,
    ValueError,
    TypeError,
    OSError,
)


def extract_shortcode(url_or_shortcode: str) -> str:
    """Extrai o shortcode de uma URL do Instagram ou valida o próprio shortcode."""
    value = url_or_shortcode.strip()
    match = SHORTCODE_URL_REGEX.search(value)
    if match:
        return match.group(1)
    cleaned = value.strip("/").split("?")[0]
    if "/" not in cleaned and re.fullmatch(r"[A-Za-z0-9_-]{5,20}", cleaned):
        return cleaned
    raise HTTPException(
        status_code=400,
        detail=f"Não foi possível extrair um shortcode válido de: '{url_or_shortcode}'",
    )


def handle_instaloader_error(exc: Exception) -> None:
    """Converte exceções do Instaloader em HTTPException do FastAPI com status adequados."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, (ProfileNotExistsException, QueryReturnedNotFoundException)):
        raise HTTPException(
            status_code=404,
            detail=str(exc) or "Recurso não encontrado no Instagram.",
        ) from exc
    if isinstance(exc, PrivateProfileNotFollowedException):
        raise HTTPException(
            status_code=403, detail=str(exc) or "Este perfil é privado."
        ) from exc
    if isinstance(exc, LoginRequiredException):
        raise HTTPException(
            status_code=401,
            detail=(
                f"{str(exc)} (Esta funcionalidade específica é restrita pelo Instagram para "
                "acesso anônimo. Caso queira utilizá-la, configure cookies de sessão em "
                "/api/v1/session/cookies)."
            ),
        ) from exc
    if isinstance(exc, TooManyRequestsException):
        raise HTTPException(
            status_code=429,
            detail=f"Limite de requisições do Instagram atingido (Rate Limit): {str(exc)}",
        ) from exc
    if isinstance(
        exc, (BadCredentialsException, TwoFactorAuthRequiredException, LoginException)
    ):
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if isinstance(exc, InvalidArgumentException):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(
        exc, (QueryReturnedBadRequestException, QueryReturnedForbiddenException)
    ):
        raise HTTPException(
            status_code=403, detail=f"Acesso recusado pelo Instagram: {str(exc)}"
        ) from exc
    if isinstance(exc, (ConnectionException, BadResponseException)):
        raise HTTPException(
            status_code=502,
            detail=f"Falha na comunicação com o Instagram: {str(exc)}",
        ) from exc
    if isinstance(exc, InstaloaderException):
        raise HTTPException(
            status_code=500, detail=f"Erro interno do Instaloader: {str(exc)}"
        ) from exc
    raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(exc)}") from exc


class InstagramScraperService:
    """Serviço central que encapsula o Instaloader para uso na API."""

    def __init__(self, download_dir: str = "downloads") -> None:
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.download_dir / ".session_cookies.json"
        self.loader = self._create_loader()
        self._load_initial_session()

    def _create_loader(self) -> Instaloader:
        return Instaloader(
            sleep=True,
            quiet=True,
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=True,
            download_geotags=False,
            download_comments=False,
            save_metadata=True,
            compress_json=False,
            dirname_pattern=str(self.download_dir / "{target}"),
            filename_pattern="{date_utc}_UTC_{shortcode}",
            max_connection_attempts=2,
            request_timeout=30.0,
            sanitize_paths=True,
        )

    def _load_initial_session(self) -> None:
        """Carrega sessão automaticamente via variáveis de ambiente (IG_SESSIONID) ou arquivo persistido."""
        env_sessionid = os.environ.get("IG_SESSIONID", "").strip()
        if env_sessionid:
            clean_sid = unquote(env_sessionid)
            env_user = os.environ.get("IG_USERNAME", "instagram_user").strip().lower()
            cookies = {
                "sessionid": clean_sid,
                "csrftoken": os.environ.get("IG_CSRFTOKEN", "missing").strip() or "missing",
            }
            if os.environ.get("IG_DS_USER_ID"):
                cookies["ds_user_id"] = os.environ["IG_DS_USER_ID"].strip()
            elif ":" in clean_sid and clean_sid.split(":", 1)[0].isdigit():
                cookies["ds_user_id"] = clean_sid.split(":", 1)[0]
            for env_key, cookie_key in (
                ("IG_MID", "mid"),
                ("IG_DID", "ig_did"),
                ("IG_RUR", "rur"),
            ):
                if os.environ.get(env_key):
                    cookies[cookie_key] = os.environ[env_key].strip()
            with suppress(Exception):
                self.loader.load_session(env_user, cookies)
            return

        if self.session_file.exists():
            with suppress(Exception):
                saved = json.loads(self.session_file.read_text(encoding="utf-8"))
                username = saved.get("username") or "instagram_user"
                cookies = saved.get("cookies") or {}
                if cookies.get("sessionid"):
                    self.loader.load_session(username, cookies)

    def get_status(self) -> dict:
        worker_url = os.environ.get("CF_WORKER_URL", "").strip()
        cf_supports_post = None
        session_diag = "not_configured"
        if self.loader.context.is_logged_in:
            status_code, final_url, text = (
                self.loader.context.fetch_authenticated_via_worker_or_direct(
                    "https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram",
                    extra_headers={"x-ig-app-id": "936619743392459"},
                )
            )
            if worker_url:
                cf_supports_post = status_code != 401 or "Instaloader" not in text
            if status_code == 200 and '"user"' in text:
                session_diag = "valid_active"
            elif "user_has_logged_out" in text or "/accounts/login" in final_url:
                session_diag = f"expired_or_logged_out (HTTP {status_code})"
            else:
                session_diag = f"http_{status_code}: {text[:120]}"
        return {
            "status": "ok",
            "instaloader_version": instaloader.__version__,
            "is_logged_in": self.loader.context.is_logged_in,
            "logged_username": self.loader.context.username,
            "cf_worker_configured": bool(worker_url),
            "cf_worker_supports_post": cf_supports_post,
            "session_status": session_diag,
        }

    def set_session_cookies(self, username: str, cookies: Dict[str, str]) -> dict:
        try:
            clean_user = username.strip().lower()
            self.loader.load_session(clean_user, cookies)
            with suppress(OSError):
                self.session_file.write_text(
                    json.dumps({"username": clean_user, "cookies": cookies}),
                    encoding="utf-8",
                )
            verified_user = self.loader.test_login()
            return {
                "status": "ok",
                "is_logged_in": self.loader.context.is_logged_in,
                "logged_username": verified_user or self.loader.context.username,
            }
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            return {}

    def login_with_credentials(self, username: str, password: str) -> dict:
        try:
            self.loader.login(username.strip(), password)
            return {
                "status": "ok",
                "is_logged_in": self.loader.context.is_logged_in,
                "logged_username": self.loader.context.username,
            }
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            return {}

    def reset_to_public_session(self) -> dict:
        with suppress(OSError):
            if self.session_file.exists():
                self.session_file.unlink()
        self.loader.close()
        self.loader = self._create_loader()
        return self.get_status()

    def get_profile(self, username: str) -> ProfileDetailSchema:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            return serialize_profile_detail(profile)
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_by_id(self, profile_id: int) -> ProfileDetailSchema:
        try:
            profile = Profile.from_id(self.loader.context, profile_id)
            return serialize_profile_detail(profile)
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_posts(
        self,
        username: str,
        limit: int = 12,
        only_videos: bool = False,
        only_pictures: bool = False,
        include_sidecar: bool = True,
    ) -> List[PostSchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            posts_iter = profile.get_posts()
            results: List[PostSchema] = []
            for post in posts_iter:
                if only_videos and not post.is_video:
                    continue
                if only_pictures and post.is_video:
                    continue
                results.append(serialize_post(post, include_sidecar=include_sidecar))
                if len(results) >= limit:
                    break
            return results
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_reels(self, username: str, limit: int = 12) -> List[PostSchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            reels_iter = profile.get_reels()
            return [serialize_post(post) for post in islice(reels_iter, limit)]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_tagged_posts(
        self, username: str, limit: int = 12
    ) -> List[PostSchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            tagged_iter = profile.get_tagged_posts()
            return [serialize_post(post) for post in islice(tagged_iter, limit)]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_igtv(self, username: str, limit: int = 12) -> List[PostSchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            igtv_iter = profile.get_igtv_posts()
            return [serialize_post(post) for post in islice(igtv_iter, limit)]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_stories(self, username: str) -> List[StorySchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            stories = self.loader.get_stories(userids=[profile.userid])
            return [serialize_story(story) for story in stories]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_highlights(
        self, username: str, include_items: bool = True
    ) -> List[HighlightSchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            highlights = self.loader.get_highlights(profile)
            return [
                serialize_highlight(hl, include_items=include_items)
                for hl in highlights
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def _scan_followers_list(
        self, profile: Profile, limit: int = 200
    ) -> Tuple[List[ProfileSummarySchema], bool]:
        """Obtém a lista nominal de seguidores via API v1 (com suporte ao Cloudflare Worker)."""
        if not self.loader.context.is_logged_in:
            return [], False
        uid_str = str(profile.userid or 0)
        v1_users = self.loader.context.fetch_followers_v1(uid_str, max_count=limit)
        if v1_users:
            items = [
                ProfileSummarySchema(
                    userid=int(u.get("pk") or u.get("id") or 0),
                    username=str(u.get("username") or ""),
                    full_name=u.get("full_name"),
                    profile_pic_url=u.get("profile_pic_url"),
                    is_private=bool(u.get("is_private", False)),
                    is_verified=bool(u.get("is_verified", False)),
                )
                for u in v1_users
                if u.get("username")
            ]
            return items, True
        return [], False

    def get_profile_followers(
        self, username: str, limit: int = 50
    ) -> List[ProfileSummarySchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            items, ok = self._scan_followers_list(profile, limit=limit)
            if ok:
                return items
            return [
                serialize_profile_summary(p)
                for p in islice(profile.get_followers(), limit)
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def check_new_followers(
        self,
        username: str,
        max_scan: int = 200,
        reset_snapshot: bool = False,
    ) -> FollowersDiffResponse:
        """Compara os seguidores atuais com a última consulta salva e retorna quantos e quem entrou."""
        clean_username = username.strip().lstrip("@").lower()
        snapshots_dir = self.download_dir / "followers_snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        snap_file = snapshots_dir / f"{clean_username}.json"

        if reset_snapshot and snap_file.exists():
            with suppress(OSError):
                snap_file.unlink()

        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            current_count = int(profile.followers or 0)
            now_utc = datetime.now(timezone.utc)

            scanned_followers, who_available = self._scan_followers_list(
                profile, limit=max_scan
            )

            current_map: Dict[str, dict] = {
                str(f.userid or f.username): f.model_dump() for f in scanned_followers
            }

            if not snap_file.exists():
                snap_payload = {
                    "username": clean_username,
                    "snapshot_at": now_utc.isoformat(),
                    "followers_count": current_count,
                    "who_available": who_available,
                    "followers_map": current_map,
                }
                snap_file.write_text(
                    json.dumps(snap_payload, ensure_ascii=False), encoding="utf-8"
                )
                msg = (
                    f"Snapshot inicial criado para @{clean_username} com {current_count} seguidores. "
                    "Faça um novo GET daqui a alguns minutos para ver os novos seguidores!"
                )
                if not who_available:
                    msg += (
                        " (Modo público: monitorando a quantidade exata de novos seguidores. "
                        "Para listar também o @username de quem seguiu, configure IG_SESSIONID no Dokploy)."
                    )
                return FollowersDiffResponse(
                    username=clean_username,
                    is_first_snapshot=True,
                    previous_snapshot_at=None,
                    current_snapshot_at=now_utc,
                    elapsed_seconds=None,
                    previous_followers_count=None,
                    current_followers_count=current_count,
                    followers_count_delta=0,
                    new_followers_count=0,
                    new_followers=[],
                    lost_followers_count=0,
                    lost_followers=[],
                    who_tracking_available=who_available,
                    message=msg,
                )

            prev_data = json.loads(snap_file.read_text(encoding="utf-8"))
            prev_at_str = prev_data.get("snapshot_at")
            prev_at = (
                datetime.fromisoformat(prev_at_str) if prev_at_str else now_utc
            )
            if prev_at.tzinfo is None:
                prev_at = prev_at.replace(tzinfo=timezone.utc)
            elapsed = round((now_utc - prev_at).total_seconds(), 2)
            prev_count = int(prev_data.get("followers_count", current_count))
            delta = current_count - prev_count
            prev_map: Dict[str, dict] = prev_data.get("followers_map") or {}

            new_followers: List[ProfileSummarySchema] = []
            lost_followers: List[ProfileSummarySchema] = []

            if who_available and prev_map:
                for key, item_dict in current_map.items():
                    if key not in prev_map:
                        new_followers.append(ProfileSummarySchema(**item_dict))
                if current_count <= max_scan and prev_count <= max_scan:
                    for key, item_dict in prev_map.items():
                        if key not in current_map:
                            lost_followers.append(ProfileSummarySchema(**item_dict))
                    merged_map = current_map
                else:
                    merged_map = {**prev_map, **current_map}
                new_count = len(new_followers) if new_followers else max(0, delta)
                lost_count = len(lost_followers) if lost_followers else max(0, -delta)
            else:
                merged_map = current_map or prev_map
                new_count = max(0, delta)
                lost_count = max(0, -delta)

            snap_payload = {
                "username": clean_username,
                "snapshot_at": now_utc.isoformat(),
                "followers_count": current_count,
                "who_available": who_available,
                "followers_map": merged_map,
            }
            snap_file.write_text(
                json.dumps(snap_payload, ensure_ascii=False), encoding="utf-8"
            )

            msg = (
                f"Comparação concluída após {elapsed}s: "
                f"{new_count} novo(s) seguidor(es) (saldo: {delta:+d}, total atual: {current_count})."
            )
            if not who_available:
                msg += (
                    " Para saber também QUEM são (@username e nome), "
                    "adicione IG_SESSIONID nas variáveis de ambiente do Dokploy."
                )

            return FollowersDiffResponse(
                username=clean_username,
                is_first_snapshot=False,
                previous_snapshot_at=prev_at,
                current_snapshot_at=now_utc,
                elapsed_seconds=elapsed,
                previous_followers_count=prev_count,
                current_followers_count=current_count,
                followers_count_delta=delta,
                new_followers_count=new_count,
                new_followers=new_followers,
                lost_followers_count=lost_count,
                lost_followers=lost_followers,
                who_tracking_available=who_available,
                message=msg,
            )
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_followees(
        self, username: str, limit: int = 50
    ) -> List[ProfileSummarySchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            return [
                serialize_profile_summary(p)
                for p in islice(profile.get_followees(), limit)
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_profile_similar_accounts(
        self, username: str, limit: int = 20
    ) -> List[ProfileSummarySchema]:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            return [
                serialize_profile_summary(p)
                for p in islice(profile.get_similar_accounts(), limit)
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_post_by_shortcode(self, shortcode_or_url: str) -> PostSchema:
        shortcode = extract_shortcode(shortcode_or_url)
        try:
            post = Post.from_shortcode(self.loader.context, shortcode)
            return serialize_post(post, include_sidecar=True)
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_post_by_mediaid(self, mediaid: int) -> PostSchema:
        try:
            post = Post.from_mediaid(self.loader.context, mediaid)
            return serialize_post(post, include_sidecar=True)
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_post_comments(
        self, shortcode_or_url: str, limit: int = 50, max_answers: int = 10
    ) -> List[CommentSchema]:
        shortcode = extract_shortcode(shortcode_or_url)
        try:
            post = Post.from_shortcode(self.loader.context, shortcode)
            if not self.loader.context.is_logged_in:
                node = getattr(post, "_node", {}) or {}
                preview_comments = node.get("preview_comments") or []
                if preview_comments:
                    results: List[CommentSchema] = []
                    for c in preview_comments[:limit]:
                        user = c.get("user") or {}
                        created_ts = c.get("created_at") or c.get("created_at_utc") or 0
                        created_dt = datetime.fromtimestamp(
                            created_ts, tz=timezone.utc
                        ).replace(tzinfo=None)
                        results.append(
                            CommentSchema(
                                id=int(c.get("pk") or c.get("id") or 0),
                                created_at_utc=created_dt,
                                text=c.get("text") or "",
                                owner_username=user.get("username") or "",
                                owner_id=int(user["pk"]) if user.get("pk") else None,
                                likes_count=int(c.get("comment_like_count") or 0),
                                answers=[],
                            )
                        )
                    return results
            comments_iter = post.get_comments()
            return [
                serialize_comment(c, max_answers=max_answers)
                for c in islice(comments_iter, limit)
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_post_likes(
        self, shortcode_or_url: str, limit: int = 50
    ) -> List[ProfileSummarySchema]:
        shortcode = extract_shortcode(shortcode_or_url)
        try:
            post = Post.from_shortcode(self.loader.context, shortcode)
            return [
                serialize_profile_summary(p) for p in islice(post.get_likes(), limit)
            ]
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_hashtag_info(self, tag_name: str) -> HashtagSchema:
        clean_tag = tag_name.strip().lstrip("#").lower()
        try:
            hashtag = Hashtag.from_name(self.loader.context, clean_tag)
            return serialize_hashtag(hashtag)
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def get_hashtag_posts(
        self,
        tag_name: str,
        limit: int = 12,
        include_top: bool = True,
        include_recent: bool = True,
    ) -> HashtagPostsResponse:
        clean_tag = tag_name.strip().lstrip("#").lower()
        try:
            hashtag = Hashtag.from_name(self.loader.context, clean_tag)
            hashtag_schema = serialize_hashtag(hashtag)
            top_posts = (
                [serialize_post(p) for p in islice(hashtag.get_top_posts(), limit)]
                if include_top
                else []
            )
            recent_posts = (
                [
                    serialize_post(p)
                    for p in islice(hashtag.get_posts_resumable(), limit)
                ]
                if include_recent
                else []
            )
            return HashtagPostsResponse(
                hashtag=hashtag_schema,
                top_posts=top_posts,
                recent_posts=recent_posts,
            )
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def search_instagram(self, query: str, limit: int = 20) -> SearchResultsSchema:
        clean_query = query.strip()
        if not clean_query:
            raise HTTPException(
                status_code=400,
                detail="O parâmetro de busca 'q' não pode ser vazio.",
            )
        try:
            search = TopSearchResults(self.loader.context, clean_query)
            profiles = [
                serialize_profile_summary(p)
                for p in islice(search.get_profiles(), limit)
            ]
            hashtags = list(islice(search.get_hashtag_strings(), limit))
            locations = [
                serialize_location(loc) for loc in islice(search.get_locations(), limit)
            ]
            return SearchResultsSchema(
                query=clean_query,
                profiles=profiles,
                hashtags=hashtags,
                locations=[loc for loc in locations if loc is not None],
            )
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def download_post_to_server(self, shortcode_or_url: str) -> DownloadResponse:
        shortcode = extract_shortcode(shortcode_or_url)
        try:
            post = Post.from_shortcode(self.loader.context, shortcode)
            target_folder = f"post_{shortcode}"
            target_dir = self.download_dir / target_folder
            target_dir.mkdir(parents=True, exist_ok=True)

            self.loader.download_post(post, target=target_folder)

            files = sorted(
                str(p.relative_to(self.download_dir)).replace("\\", "/")
                for p in target_dir.rglob("*")
                if p.is_file()
            )
            static_urls = [f"/downloads/{rel_path}" for rel_path in files]
            return DownloadResponse(
                target=shortcode,
                directory=str(target_dir),
                files=files,
                static_urls=static_urls,
            )
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def download_profile_to_server(
        self, username: str, limit: int = 6, include_profile_pic: bool = True
    ) -> DownloadResponse:
        clean_username = username.strip().lstrip("@").lower()
        try:
            profile = Profile.from_username(self.loader.context, clean_username)
            target_dir = self.download_dir / clean_username
            target_dir.mkdir(parents=True, exist_ok=True)

            if include_profile_pic:
                self.loader.download_profilepic(profile)

            if limit > 0:
                for post in islice(profile.get_posts(), limit):
                    self.loader.download_post(post, target=clean_username)

            files = sorted(
                str(p.relative_to(self.download_dir)).replace("\\", "/")
                for p in target_dir.rglob("*")
                if p.is_file()
            )
            static_urls = [f"/downloads/{rel_path}" for rel_path in files]
            return DownloadResponse(
                target=clean_username,
                directory=str(target_dir),
                files=files,
                static_urls=static_urls,
            )
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

    def fetch_media_stream(self, media_url: str) -> Tuple[bytes, str, str]:
        """Baixa os bytes brutos de uma URL de mídia do CDN do Instagram para proxy/download."""
        parsed = urlparse(media_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(status_code=400, detail="URL de mídia inválida.")
        try:
            resp = self.loader.context.get_raw(media_url)
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            filename = os.path.basename(parsed.path) or "instagram_media"
            if "." not in filename:
                ext = "mp4" if "video" in content_type else "jpg"
                filename = f"{filename}.{ext}"
            return resp.content, content_type, filename
        except HANDLED_EXCEPTIONS as exc:
            handle_instaloader_error(exc)
            raise

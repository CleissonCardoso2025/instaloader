"""Funções de serialização segura das estruturas do Instaloader para schemas Pydantic."""

from itertools import islice
from typing import Any, Callable, List, Optional

from instaloader.exceptions import InstaloaderException
from instaloader.structures import (
    Hashtag,
    Highlight,
    Post,
    PostComment,
    PostLocation,
    Profile,
    Story,
    StoryItem,
)

from .schemas import (
    CommentAnswerSchema,
    CommentSchema,
    HashtagSchema,
    HighlightSchema,
    LocationSchema,
    PostSchema,
    ProfileDetailSchema,
    ProfileSummarySchema,
    SidecarNodeSchema,
    StoryItemSchema,
    StorySchema,
)


def _safe_get(getter: Callable[[], Any], default: Any = None) -> Any:
    """Executa um getter capturando exceções de login, chave ausente ou erro do Instaloader."""
    try:
        return getter()
    except (InstaloaderException, KeyError, IndexError, TypeError, ValueError):
        return default


def serialize_profile_summary(profile: Profile) -> ProfileSummarySchema:
    node = getattr(profile, "_node", {}) or {}
    userid = _safe_get(lambda: profile.userid, node.get("id") or node.get("pk"))
    username = _safe_get(lambda: profile.username, node.get("username", ""))
    full_name = _safe_get(lambda: profile.full_name, node.get("full_name"))
    is_private = _safe_get(lambda: profile.is_private, node.get("is_private"))
    is_verified = _safe_get(lambda: profile.is_verified, node.get("is_verified"))
    profile_pic_url = _safe_get(
        lambda: profile.profile_pic_url,
        node.get("profile_pic_url_hd") or node.get("profile_pic_url"),
    )
    return ProfileSummarySchema(
        userid=int(userid) if userid is not None else None,
        username=username,
        full_name=full_name,
        is_private=is_private,
        is_verified=is_verified,
        profile_pic_url=profile_pic_url,
    )


def serialize_profile_detail(profile: Profile) -> ProfileDetailSchema:
    summary = serialize_profile_summary(profile)
    node = getattr(profile, "_node", {}) or {}

    external_url = _safe_get(lambda: profile.external_url, node.get("external_url"))
    is_business_account = _safe_get(
        lambda: profile.is_business_account,
        node.get("is_business_account", node.get("is_business")),
    )
    business_category_name = _safe_get(
        lambda: profile.business_category_name,
        node.get(
            "business_category_name",
            node.get("category_name") or node.get("category"),
        ),
    )
    bio_links = node.get("bio_links") or []

    return ProfileDetailSchema(
        **summary.model_dump(),
        biography=_safe_get(lambda: profile.biography, node.get("biography")),
        biography_hashtags=_safe_get(lambda: profile.biography_hashtags, []),
        biography_mentions=_safe_get(lambda: profile.biography_mentions, []),
        external_url=external_url,
        bio_links=bio_links if isinstance(bio_links, list) else [],
        followers=_safe_get(lambda: profile.followers),
        followees=_safe_get(lambda: profile.followees),
        mediacount=_safe_get(lambda: profile.mediacount),
        igtvcount=_safe_get(lambda: profile.igtvcount),
        is_business_account=is_business_account,
        business_category_name=business_category_name,
        instagram_url=f"https://www.instagram.com/{summary.username}/",
    )


def serialize_location(
    loc: Optional[PostLocation], raw_loc: Optional[dict] = None
) -> Optional[LocationSchema]:
    if loc is not None:
        return LocationSchema(
            id=loc.id,
            name=loc.name,
            slug=loc.slug,
            has_public_page=loc.has_public_page,
            lat=loc.lat,
            lng=loc.lng,
        )
    if isinstance(raw_loc, dict) and (
        raw_loc.get("id") or raw_loc.get("pk") or raw_loc.get("name")
    ):
        loc_id = raw_loc.get("id") or raw_loc.get("pk")
        return LocationSchema(
            id=int(loc_id) if loc_id is not None else None,
            name=raw_loc.get("name"),
            slug=raw_loc.get("slug"),
            has_public_page=raw_loc.get("has_public_page"),
            lat=raw_loc.get("lat"),
            lng=raw_loc.get("lng"),
        )
    return None


def serialize_post(post: Post, include_sidecar: bool = True) -> PostSchema:
    node = getattr(post, "_node", {}) or {}
    shortcode = post.shortcode
    typename = _safe_get(lambda: post.typename, node.get("__typename", "GraphImage"))

    sidecar_nodes: List[SidecarNodeSchema] = []
    if include_sidecar and typename == "GraphSidecar":
        raw_nodes = _safe_get(lambda: list(post.get_sidecar_nodes()), [])
        for idx, snode in enumerate(raw_nodes, start=1):
            sidecar_nodes.append(
                SidecarNodeSchema(
                    index=idx,
                    is_video=snode.is_video,
                    display_url=snode.display_url,
                    video_url=snode.video_url,
                )
            )

    loc_obj = _safe_get(lambda: post.location, None)
    raw_loc = node.get("location")
    location = serialize_location(loc_obj, raw_loc)

    owner_username = _safe_get(
        lambda: post.owner_username,
        (node.get("owner") or {}).get("username")
        or (node.get("user") or {}).get("username"),
    )
    owner_id = _safe_get(
        lambda: post.owner_id,
        (node.get("owner") or {}).get("id") or (node.get("user") or {}).get("pk"),
    )

    is_video = _safe_get(lambda: post.is_video, bool(node.get("is_video", False)))
    video_url = (
        _safe_get(lambda: post.video_url, node.get("video_url")) if is_video else None
    )

    return PostSchema(
        shortcode=shortcode,
        mediaid=post.mediaid,
        instagram_url=f"https://www.instagram.com/p/{shortcode}/",
        typename=typename,
        date_utc=post.date_utc,
        date_local=post.date_local,
        owner_username=owner_username,
        owner_id=int(owner_id) if owner_id is not None else None,
        title=_safe_get(lambda: post.title),
        caption=_safe_get(lambda: post.caption),
        caption_hashtags=_safe_get(lambda: post.caption_hashtags, []),
        caption_mentions=_safe_get(lambda: post.caption_mentions, []),
        accessibility_caption=_safe_get(lambda: post.accessibility_caption),
        tagged_users=_safe_get(lambda: post.tagged_users, []),
        is_video=is_video,
        url=_safe_get(lambda: post.url, node.get("display_url") or ""),
        video_url=video_url,
        video_duration=_safe_get(lambda: post.video_duration) if is_video else None,
        video_view_count=_safe_get(lambda: post.video_view_count) if is_video else None,
        video_play_count=_safe_get(lambda: post.video_play_count) if is_video else None,
        likes=_safe_get(lambda: post.likes),
        comments_count=_safe_get(lambda: post.comments),
        mediacount=_safe_get(lambda: post.mediacount, len(sidecar_nodes) or 1),
        is_sponsored=_safe_get(lambda: post.is_sponsored, False),
        sponsor_users=_safe_get(lambda: [u.username for u in post.sponsor_users], []),
        location=location,
        sidecar_nodes=sidecar_nodes,
    )


def serialize_comment(comment: PostComment, max_answers: int = 20) -> CommentSchema:
    answers_list: List[CommentAnswerSchema] = []
    raw_answers = _safe_get(lambda: list(islice(comment.answers, max_answers)), [])
    for ans in raw_answers:
        answers_list.append(
            CommentAnswerSchema(
                id=ans.id,
                created_at_utc=ans.created_at_utc,
                text=ans.text,
                owner_username=_safe_get(lambda a=ans: a.owner.username, ""),
                owner_id=_safe_get(lambda a=ans: a.owner.userid),
                likes_count=ans.likes_count,
            )
        )
    return CommentSchema(
        id=comment.id,
        created_at_utc=comment.created_at_utc,
        text=comment.text,
        owner_username=_safe_get(lambda: comment.owner.username, ""),
        owner_id=_safe_get(lambda: comment.owner.userid),
        likes_count=_safe_get(lambda: comment.likes_count, 0),
        answers=answers_list,
    )


def serialize_story_item(item: StoryItem) -> StoryItemSchema:
    is_video = _safe_get(lambda: item.is_video, False)
    return StoryItemSchema(
        mediaid=item.mediaid,
        shortcode=item.shortcode,
        typename=_safe_get(lambda: item.typename),
        date_utc=item.date_utc,
        expiring_utc=_safe_get(lambda: item.expiring_utc),
        is_video=is_video,
        url=_safe_get(lambda: item.url, ""),
        video_url=_safe_get(lambda: item.video_url) if is_video else None,
        caption=_safe_get(lambda: item.caption),
        caption_hashtags=_safe_get(lambda: item.caption_hashtags, []),
        caption_mentions=_safe_get(lambda: item.caption_mentions, []),
        owner_username=_safe_get(lambda: item.owner_username),
        owner_id=_safe_get(lambda: item.owner_id),
    )


def serialize_story(story: Story) -> StorySchema:
    items = [
        serialize_story_item(item)
        for item in _safe_get(lambda: list(story.get_items()), [])
    ]
    return StorySchema(
        owner_username=_safe_get(lambda: story.owner_username, ""),
        owner_id=_safe_get(lambda: story.owner_id, 0),
        latest_media_utc=_safe_get(lambda: story.latest_media_utc),
        itemcount=len(items),
        items=items,
    )


def serialize_highlight(
    highlight: Highlight, include_items: bool = True
) -> HighlightSchema:
    items = (
        [
            serialize_story_item(item)
            for item in _safe_get(lambda: list(highlight.get_items()), [])
        ]
        if include_items
        else []
    )
    return HighlightSchema(
        unique_id=highlight.unique_id,
        title=_safe_get(lambda: highlight.title, ""),
        owner_username=_safe_get(lambda: highlight.owner_username, ""),
        owner_id=_safe_get(lambda: highlight.owner_id, 0),
        cover_url=_safe_get(lambda: highlight.cover_url),
        cover_cropped_url=_safe_get(lambda: highlight.cover_cropped_url),
        itemcount=_safe_get(lambda: highlight.itemcount, len(items)),
        items=items,
    )


def serialize_hashtag(hashtag: Hashtag) -> HashtagSchema:
    name = hashtag.name
    return HashtagSchema(
        name=name,
        hashtagid=_safe_get(lambda: hashtag.hashtagid),
        mediacount=_safe_get(lambda: hashtag.mediacount),
        description=_safe_get(lambda: hashtag.description),
        profile_pic_url=_safe_get(lambda: hashtag.profile_pic_url),
        allow_following=_safe_get(lambda: hashtag.allow_following),
        instagram_url=f"https://www.instagram.com/explore/tags/{name}/",
    )

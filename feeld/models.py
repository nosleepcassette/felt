# maps · cassette.help · MIT
"""
Data models for Feeld API responses.

These are dataclasses that normalize the raw GraphQL response
into predictable Python objects. Field names are placeholders
that should be updated once real schema is known from Task 0 recon.

If a field from the API doesn't match, update the `from_dict` classmethod
rather than the dataclass fields — keep the dataclass as the stable interface.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Photo:
    url: str
    width: int = 0
    height: int = 0
    is_primary: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Photo":
        return cls(
            url=d.get("url") or d.get("src") or d.get("photoUrl", ""),
            width=d.get("width", 0),
            height=d.get("height", 0),
            is_primary=d.get("isPrimary") or d.get("primary", False),
        )


@dataclass
class Profile:
    """A Feeld user profile."""
    id: str
    display_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    desires: list[str] = field(default_factory=list)
    photos: list[Photo] = field(default_factory=list)
    bio: Optional[str] = None
    location: Optional[str] = None
    partner_display_name: Optional[str] = None  # for couples/connections

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        photos_raw = d.get("photos") or d.get("images") or []
        photos = [Photo.from_dict(p) for p in photos_raw]

        return cls(
            id=d.get("id") or d.get("userId", "unknown"),
            display_name=(
                d.get("displayName")
                or d.get("name")
                or d.get("username")
                or "Unknown"
            ),
            age=d.get("age"),
            gender=d.get("gender") or d.get("genderIdentity"),
            desires=d.get("desires") or d.get("desiresList") or [],
            photos=photos,
            bio=d.get("bio") or d.get("description"),
            location=d.get("location") or d.get("city"),
            partner_display_name=d.get("partnerDisplayName"),
        )

    @property
    def primary_photo_url(self) -> str:
        """Return the primary photo URL or empty string."""
        primary = [p for p in self.photos if p.is_primary]
        if primary:
            return primary[0].url
        if self.photos:
            return self.photos[0].url
        return ""


@dataclass
class SwipeEvent:
    """Someone swiped on your profile (like or pass)."""
    id: str
    profile: Profile
    action: str  # "like" or "pass"
    created_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict, action: str = "unknown") -> "SwipeEvent":
        # The profile might be nested under "profile", "user", "member", etc.
        profile_data = (
            d.get("profile")
            or d.get("user")
            or d.get("member")
            or d.get("sender")
            or d
        )

        created_raw = d.get("createdAt") or d.get("created_at") or d.get("timestamp")
        created_at = None
        if created_raw:
            try:
                if isinstance(created_raw, (int, float)):
                    created_at = datetime.fromtimestamp(created_raw / 1000)
                else:
                    created_at = datetime.fromisoformat(
                        str(created_raw).replace("Z", "+00:00")
                    )
            except (ValueError, TypeError):
                pass

        return cls(
            id=d.get("id", ""),
            profile=Profile.from_dict(profile_data),
            action=action,
            created_at=created_at,
            raw=d,
        )

    @property
    def time_ago(self) -> str:
        """Human-readable time since this event."""
        if not self.created_at:
            return "unknown"
        delta = datetime.now() - self.created_at.replace(tzinfo=None)
        seconds = int(delta.total_seconds())
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"


@dataclass
class Match:
    """A mutual like / connection."""
    id: str
    profile: Profile
    matched_at: Optional[datetime] = None
    last_message: Optional[str] = None
    unread_count: int = 0
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Match":
        profile_data = (
            d.get("profile")
            or d.get("user")
            or d.get("member")
            or d.get("partner")
            or d
        )

        matched_raw = d.get("matchedAt") or d.get("createdAt") or d.get("timestamp")
        matched_at = None
        if matched_raw:
            try:
                if isinstance(matched_raw, (int, float)):
                    matched_at = datetime.fromtimestamp(matched_raw / 1000)
                else:
                    matched_at = datetime.fromisoformat(
                        str(matched_raw).replace("Z", "+00:00")
                    )
            except (ValueError, TypeError):
                pass

        return cls(
            id=d.get("id", ""),
            profile=Profile.from_dict(profile_data),
            matched_at=matched_at,
            last_message=d.get("lastMessage") or d.get("lastMessageText"),
            unread_count=d.get("unreadCount") or d.get("unread", 0),
            raw=d,
        )

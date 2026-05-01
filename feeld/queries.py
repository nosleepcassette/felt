# maps · cassette.help · MIT
"""
Feeld GraphQL query definitions and high-level fetch functions.

IMPORTANT: Query field names are placeholders until confirmed via introspection.
Look for `# CONFIRM_FIELD_NAME` comments and update each one after running:
    python3 scripts/introspect.py

The function signatures and return types are stable regardless of field names.
"""

from feeld.client import FeeldClient
from feeld.models import Match, Profile, SwipeEvent

# ---------------------------------------------------------------------------
# Query strings
# Field names marked CONFIRM_FIELD_NAME must be verified against real schema.
# ---------------------------------------------------------------------------

# Your own profile
ME_QUERY = """
query Me {
  me {  # CONFIRM_FIELD_NAME: may be "currentUser", "profile", "myProfile"
    id
    displayName  # CONFIRM_FIELD_NAME: may be "name", "username"
    age
    gender  # CONFIRM_FIELD_NAME: may be "genderIdentity"
    bio
    desires  # CONFIRM_FIELD_NAME: may be "desiresList", "desires { name }"
    photos {  # CONFIRM_FIELD_NAME: may be "images", "profilePhotos"
      url  # CONFIRM_FIELD_NAME: may be "src", "photoUrl"
      isPrimary  # CONFIRM_FIELD_NAME: may be "primary", "isMain"
    }
  }
}
"""

# People who liked you
LIKES_RECEIVED_QUERY = """
query LikesReceived($first: Int, $after: String) {
  likesReceived(first: $first, after: $after) {  # CONFIRM_FIELD_NAME
    edges {
      node {
        id
        createdAt  # CONFIRM_FIELD_NAME: may be "timestamp"
        profile {  # CONFIRM_FIELD_NAME: may be "user", "sender"
          id
          displayName
          age
          photos { url isPrimary }
          desires
          bio
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# People who passed on you
# This is the feature the app hides. May not exist as a query.
# Check RECON-queries.txt for: passes, dislikes, swipedNo, passedOnMe, declines
PASSES_RECEIVED_QUERY = """
query PassesReceived($first: Int, $after: String) {
  passesReceived(first: $first, after: $after) {  # CONFIRM_FIELD_NAME — may not exist
    edges {
      node {
        id
        createdAt
        profile {
          id
          displayName
          age
          photos { url isPrimary }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# Your matches (mutual likes)
MATCHES_QUERY = """
query Matches($first: Int, $after: String) {
  myMatches(first: $first, after: $after) {  # CONFIRM_FIELD_NAME: may be "connections", "matches"
    edges {
      node {
        id
        createdAt  # CONFIRM_FIELD_NAME: may be "matchedAt"
        unreadCount  # CONFIRM_FIELD_NAME: may not exist
        lastMessage  # CONFIRM_FIELD_NAME: may be "lastMessageText"
        profile {  # CONFIRM_FIELD_NAME: may be "partner", "user"
          id
          displayName
          age
          photos { url isPrimary }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

# Stats — how many people have seen/swiped on your profile
# This is the aggregate view (4,106 passes count from the reverser's test)
PROFILE_STATS_QUERY = """
query ProfileStats {
  profileStats {  # CONFIRM_FIELD_NAME: may be "myStats", "swipeStats"
    totalLikes  # CONFIRM_FIELD_NAME
    totalPasses  # CONFIRM_FIELD_NAME: may be "totalDislikes"
    totalViews  # CONFIRM_FIELD_NAME: may not exist
    likeRate  # CONFIRM_FIELD_NAME: may not exist
  }
}
"""


# ---------------------------------------------------------------------------
# High-level fetch functions
# These are what the web app and TUI actually call.
# ---------------------------------------------------------------------------

def fetch_me(client: FeeldClient) -> Profile:
    """Fetch your own profile."""
    data = client.query(ME_QUERY)
    # Try common field names for "me"
    me_data = (
        data.get("me")
        or data.get("currentUser")
        or data.get("myProfile")
        or data.get("profile")
        or {}
    )
    return Profile.from_dict(me_data)


def fetch_likes_received(client: FeeldClient, limit: int = 100) -> list[SwipeEvent]:
    """
    Fetch people who liked you, most recent first.

    If the query name is wrong (CONFIRM_FIELD_NAME not updated), this will
    return an empty list and print a warning — it will not crash.
    """
    try:
        nodes = client.paginate(
            LIKES_RECEIVED_QUERY,
            {"first": min(limit, 50)},
            data_path=["likesReceived"],  # CONFIRM_FIELD_NAME — update this too
        )
        return [SwipeEvent.from_dict(n, action="like") for n in nodes[:limit]]
    except Exception as e:
        print(f"[warn] fetch_likes_received failed: {e}")
        print("Check that LIKES_RECEIVED_QUERY field names match your schema (run introspect.py)")
        return []


def fetch_passes_received(client: FeeldClient, limit: int = 100) -> list[SwipeEvent]:
    """
    Fetch people who passed on you.

    This may not be available — Feeld may not expose this endpoint.
    Returns empty list rather than crashing if query fails.
    """
    try:
        nodes = client.paginate(
            PASSES_RECEIVED_QUERY,
            {"first": min(limit, 50)},
            data_path=["passesReceived"],  # CONFIRM_FIELD_NAME
        )
        return [SwipeEvent.from_dict(n, action="pass") for n in nodes[:limit]]
    except Exception as e:
        print(f"[warn] fetch_passes_received failed: {e}")
        print("The passes/dislikes endpoint may not be exposed by Feeld's API.")
        print("Check RECON-queries.txt for alternative field names.")
        return []


def fetch_matches(client: FeeldClient, limit: int = 100) -> list[Match]:
    """Fetch your current matches."""
    try:
        nodes = client.paginate(
            MATCHES_QUERY,
            {"first": min(limit, 50)},
            data_path=["myMatches"],  # CONFIRM_FIELD_NAME
        )
        return [Match.from_dict(n) for n in nodes[:limit]]
    except Exception as e:
        print(f"[warn] fetch_matches failed: {e}")
        return []


def fetch_profile_stats(client: FeeldClient) -> dict:
    """Fetch aggregate profile stats (total likes, passes, etc.)."""
    try:
        data = client.query(PROFILE_STATS_QUERY)
        stats = (
            data.get("profileStats")
            or data.get("myStats")
            or data.get("swipeStats")
            or {}
        )
        return stats
    except Exception as e:
        print(f"[warn] fetch_profile_stats failed: {e}")
        return {}

# maps · cassette.help · MIT
"""
Feeld GraphQL query definitions and high-level fetch functions.

Queries sourced from the reverse-engineered iOS app
(github.com/niewiemczego/Feeld). These are the REAL field names,
not placeholders.

The Feeld API uses:
- Base URL: https://core.api.fldcore.com/graphql
- Auth: Bearer token from Firebase (idToken)
- Headers: x-app-version, x-device-os, user-agent: feeld-mobile
- Pagination: cursor-based via `cursor` variable + `hasNextPage`/`nextPageCursor`
"""

from feeld.client import FeeldClient
from feeld.models import Match, Profile, SwipeEvent

# ---------------------------------------------------------------------------
# CONFIRMED queries — field names from working reverse-engineered code
# ---------------------------------------------------------------------------

# Your own profile + account data
AUTH_PROVIDER_QUERY = """
query AuthProviderQuery {
  account {
    id
    email
    analyticsId
    status
    isFinishedOnboarding
    isMajestic
    upliftExpirationTimestamp
    isUplift
    isDistanceInMiles
    language
    location {
      device {
        country
        __typename
      }
      __typename
    }
    profiles {
      id
      streamToken
      streamUserId
      imaginaryName
      bio
      age
      gender
      sexuality
      desires
      interests
      lookingFor
      isMajestic
      isVerified
      isIncognito
      isUplift
      lastSeen
      status
      distanceMax
      recentlyOnline
      photos {
        id
        pictureUrl
        pictureStatus
        pictureType
        publicId
        __typename
      }
      location {
        ...ProfileLocationFragment
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment ProfileLocationFragment on ProfileLocation {
  ... on DeviceLocation {
    device {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VirtualLocation {
    core
    __typename
  }
  ... on TeleportLocation {
    current: device {
      city
      country
      __typename
    }
    teleport {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""

# People who liked you
WHO_LIKES_ME_QUERY = """
query WhoLikesMe($limit: Int, $cursor: String, $sortBy: SortBy!) {
  interactions: whoLikesMe(
    input: {sortBy: $sortBy}
    limit: $limit
    cursor: $cursor
  ) {
    nodes {
      id
      age
      gender
      status
      lastSeen
      isUplift
      sexuality
      isMajestic
      isVerified
      dateOfBirth
      streamUserId
      imaginaryName
      interactionStatus {
        message
        mine
        theirs
        __typename
      }
      distance {
        km
        mi
        __typename
      }
      location {
        ...ProfileLocationFragment
        __typename
      }
      photos {
        id
        pictureUrl
        pictureStatus
        pictureType
        publicId
        __typename
      }
      __typename
    }
    pageInfo {
      total
      hasNextPage
      nextPageCursor
      __typename
    }
    __typename
  }
}

fragment ProfileLocationFragment on ProfileLocation {
  ... on DeviceLocation {
    device {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VirtualLocation {
    core
    __typename
  }
  ... on TeleportLocation {
    current: device {
      city
      country
      __typename
    }
    teleport {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""

# People who pinged you
WHO_PINGS_ME_QUERY = """
query WhoPingsMe($limit: Int, $cursor: String, $sortBy: SortBy!) {
  interactions: whoPingsMe(
    input: {sortBy: $sortBy}
    limit: $limit
    cursor: $cursor
  ) {
    nodes {
      id
      age
      gender
      status
      lastSeen
      isUplift
      sexuality
      isMajestic
      isVerified
      imaginaryName
      interactionStatus {
        message
        mine
        theirs
        __typename
      }
      distance {
        km
        mi
        __typename
      }
      photos {
        id
        pictureUrl
        pictureStatus
        pictureType
        publicId
        __typename
      }
      __typename
    }
    pageInfo {
      total
      hasNextPage
      nextPageCursor
      __typename
    }
    __typename
  }
}
"""

# Discovery — profiles to swipe on
DISCOVER_PROFILES_QUERY = """
query DiscoverProfiles($input: ProfileDiscoveryInput!) {
  discovery(input: $input) {
    nodes {
      bio
      age
      dateOfBirth
      desires
      gender
      id
      status
      imaginaryName
      interactionStatus {
        message
        mine
        theirs
        __typename
      }
      interests
      isMajestic
      isVerified
      lastSeen
      sexuality
      photos {
        id
        pictureUrl
        pictureStatus
        pictureType
        publicId
        __typename
      }
      distance {
        km
        mi
        __typename
      }
      location {
        ...ProfileLocationFragment
        __typename
      }
      __typename
    }
    hasNextBatch
    profileInSync
    feedGeneratedAt
    generatedWithProfileUpdatedAt
    feedSize
    feedCapacity
    __typename
  }
}

fragment ProfileLocationFragment on ProfileLocation {
  ... on DeviceLocation {
    device {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VirtualLocation {
    core
    __typename
  }
  ... on TeleportLocation {
    current: device {
      city
      country
      __typename
    }
    teleport {
      latitude
      longitude
      geocode {
        city
        country
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""

# Matches / chat summaries
HEADER_SUMMARIES_QUERY = """
query HeaderSummaries($limit: Int, $cursor: String) {
  summaries: getChatSummariesForChatHeader(limit: $limit, cursor: $cursor) {
    nodes {
      id
      name
      type
      status
      avatarSet
      memberCount
      latestMessage
      streamChannelId
      targetProfileId
      enableChatContentModeration
      __typename
    }
    pageInfo {
      hasNextPage
      nextPageCursor
      __typename
    }
    __typename
  }
}
"""

# Mutations
LIKE_MUTATION = """
mutation ProfileLike($targetProfileId: String!) {
  profileLike(input: {targetProfileId: $targetProfileId}) {
    status
    chat {
      id
      name
      type
      streamChatId
      status
      __typename
    }
    __typename
  }
}
"""

DISLIKE_MUTATION = """
mutation ProfileDislike($targetProfileId: String!) {
  profileDislike(input: {targetProfileId: $targetProfileId})
}
"""

PING_MUTATION = """
mutation ProfilePing($targetProfileId: String!, $message: String, $overrideInappropriate: Boolean) {
  profilePing(
    input: {targetProfileId: $targetProfileId, message: $message, overrideInappropriate: $overrideInappropriate}
  ) {
    status
    chat {
      id
      __typename
    }
    account {
      id
      availablePings
      __typename
    }
    __typename
  }
}
"""

ACCEPT_PING_MUTATION = """
mutation ProfileAcceptPing($targetProfileId: String!) {
  profileAcceptPing(input: {targetProfileId: $targetProfileId}) {
    status
    chat {
      id
      __typename
    }
    __typename
  }
}
"""

BLOCK_MUTATION = """
mutation ProfileBlock($input: ProfileBlockInteractionInput!) {
  profileBlock(input: $input)
}
"""

UPDATE_LAST_SEEN_MUTATION = """
mutation LastSeenProviderUpdateProfile($profileId: String!) {
  updatedProfileLastSeen: profileUpdateLastSeen(profileId: $profileId)
}
"""

# ---------------------------------------------------------------------------
# High-level fetch functions
# These are what the web app and TUI actually call.
# ---------------------------------------------------------------------------

def fetch_me(client: FeeldClient) -> dict:
    """Fetch your own account + profile data."""
    data = client.query(AUTH_PROVIDER_QUERY, operation_name="AuthProviderQuery")
    return data.get("account", {})


def fetch_likes_received(client: FeeldClient, sort_by: str = "LAST_INTERACTION") -> list[dict]:
    """
    Fetch people who liked you.

    sort_by: "LAST_INTERACTION", "LAST_ONLINE", or "DISTANCE"
    (Majestic required for anything other than LAST_INTERACTION)
    """
    data = client.query(
        WHO_LIKES_ME_QUERY,
        variables={"sortBy": sort_by},
        operation_name="WhoLikesMe",
    )
    interactions = data.get("interactions", {})
    nodes = interactions.get("nodes", [])
    page_info = interactions.get("pageInfo", {})
    total = page_info.get("total", len(nodes))
    print(f"  {total} likes total, fetched {len(nodes)}")
    return nodes


def fetch_pings_received(client: FeeldClient, sort_by: str = "LAST_INTERACTION", limit: int = 10) -> list[dict]:
    """Fetch people who pinged you."""
    data = client.query(
        WHO_PINGS_ME_QUERY,
        variables={"sortBy": sort_by, "limit": limit},
        operation_name="WhoPingsMe",
    )
    interactions = data.get("interactions", {})
    return interactions.get("nodes", [])


def fetch_matches(client: FeeldClient, limit: int = 10) -> list[dict]:
    """Fetch your current matches / chat summaries."""
    data = client.query(
        HEADER_SUMMARIES_QUERY,
        variables={"limit": limit},
        operation_name="HeaderSummaries",
    )
    summaries = data.get("summaries", {})
    return summaries.get("nodes", [])


def fetch_discovery(client: FeeldClient, age_range: list = None, max_distance: int = 400) -> list[dict]:
    """
    Fetch profiles to swipe on.

    age_range: e.g. [18, 45] or [18, None] for no upper bound
    max_distance: in km (5-400)
    """
    if age_range is None:
        age_range = [18, None]

    data = client.query(
        DISCOVER_PROFILES_QUERY,
        variables={
            "input": {
                "filters": {
                    "ageRange": age_range,
                    "maxDistance": max_distance,
                    "lookingFor": [
                        "MAN", "WOMAN", "MAN_WOMAN_COUPLE", "MAN_MAN_COUPLE",
                        "WOMAN_WOMAN_COUPLE", "AGENDER", "ANDROGYNOUS", "BIGENDER",
                        "GENDER_FLUID", "GENDER_NONCONFORMING", "TRANS_WOMAN",
                        "TRANS_NON_BINARY", "TRANS_MAN", "TRANS_HUMAN",
                        "TRANSMASCULINE", "TRANSFEMININE", "PANGENDER", "OTHER",
                        "NON_BINARY", "INTERSEX", "GENDER_QUESTIONING",
                        "GENDER_QUEER", "TWO_SPIRIT",
                    ],
                    "recentlyOnline": False,
                }
            }
        },
        operation_name="DiscoverProfiles",
    )
    discovery = data.get("discovery", {})
    return discovery.get("nodes", [])


def send_like(client: FeeldClient, target_profile_id: str) -> bool:
    """Like a profile."""
    try:
        client.query(
            LIKE_MUTATION,
            variables={"targetProfileId": target_profile_id},
            operation_name="ProfileLike",
        )
        return True
    except Exception as e:
        print(f"[warn] send_like failed: {e}")
        return False


def send_dislike(client: FeeldClient, target_profile_id: str) -> bool:
    """Pass on a profile."""
    try:
        client.query(
            DISLIKE_MUTATION,
            variables={"targetProfileId": target_profile_id},
            operation_name="ProfileDislike",
        )
        return True
    except Exception as e:
        print(f"[warn] send_dislike failed: {e}")
        return False


def send_ping(client: FeeldClient, target_profile_id: str, message: str = "") -> bool:
    """Send a ping to a profile."""
    try:
        client.query(
            PING_MUTATION,
            variables={
                "targetProfileId": target_profile_id,
                "message": message or None,
                "overrideInappropriate": False,
            },
            operation_name="ProfilePing",
        )
        return True
    except Exception as e:
        print(f"[warn] send_ping failed: {e}")
        return False

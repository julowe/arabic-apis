import requests


def get_access_token(url_base: str, client_id: str, client_secret: str) -> str:
    """Request an OAuth2 access token from Quran.com and return the raw token string."""
    response = requests.post(
        url_base + "/oauth2/token",
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="grant_type=client_credentials&scope=content",
    )
    return response.json()["access_token"]


def get_recitations(url_base: str, access_token: str, client_id: str):
    """Return raw JSON listing available recitations."""
    response = requests.get(
        url_base + "/content/api/v4/resources/recitations",
        headers={
            "Accept": "application/json",
            "x-auth-token": access_token,
            "x-client-id": client_id,
        },
    )
    return response.json()


def get_recitation_filelist(
    url_base: str,
    access_token: str,
    client_id: str,
    recitation_id: int,
    chapter_number: int,
    page: int | None = None,
    per_page: int | None = None,
):
    """Return raw JSON for a single page of audio files for a recitation and chapter.

    Pagination parameters are passed through without aggregation to keep this layer simple.
    """
    query = ""
    if page is not None:
        query += ("?" if not query else "&") + f"page={page}"
    if per_page is not None:
        query += ("?" if not query else "&") + f"per_page={per_page}"

    response = requests.get(
        url_base
        + "/content/api/v4/recitations/"
        + str(recitation_id)
        + "/by_chapter/"
        + str(chapter_number)
        + query,
        headers={
            "Accept": "application/json",
            "x-auth-token": access_token,
            "x-client-id": client_id,
        },
    )
    return response.json()


def get_chapter(
    url_base: str, access_token: str, client_id: str, chapter_number: int | None = None
):
    """Return raw JSON for chapter list or a specific chapter."""
    if chapter_number:
        url_request = url_base + "/content/api/v4/chapters/" + str(chapter_number)
    else:
        url_request = url_base + "/content/api/v4/chapters/"

    response = requests.get(
        url_request,
        headers={"x-auth-token": access_token, "x-client-id": client_id},
    )
    return response.json()


def get_verse(
    url_base: str,
    access_token: str,
    client_id: str,
    chapter_number: int,
    verse_number: int,
    fields: list[str] | None = None,
    translations: list[int] | None = None,
):
    """Return raw JSON for a verse by key. Optional fields and translations can be provided.

    This function does not post-process any data; it only returns the response JSON.
    """
    query_parts = []
    if fields:
        query_parts.append("fields=" + ",".join(fields))
    if translations:
        query_parts.append("translations=" + ",".join(str(t) for t in translations))
    query = ("?" + "&".join(query_parts)) if query_parts else ""

    response = requests.get(
        url_base
        + "/content/api/v4/verses/by_key/"
        + f"{chapter_number}:{verse_number}"
        + query,
        headers={
            "Accept": "application/json",
            "x-auth-token": access_token,
            "x-client-id": client_id,
        },
    )
    return response.json()


def get_translations(url_base: str, access_token: str, client_id: str):
    """Return raw JSON listing translation resources."""
    response = requests.get(
        url_base + "/content/api/v4/resources/translations",
        headers={
            "Accept": "application/json",
            "x-auth-token": access_token,
            "x-client-id": client_id,
        },
    )
    return response.json()

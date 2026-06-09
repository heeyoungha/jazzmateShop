from types import SimpleNamespace


REVIEW_ID = 7
REVIEW_CONTENT = "차분하고 공간감 있는 모달 재즈가 인상적입니다."
ALBUM_ID_1 = "00000000-0000-0000-0000-000000000101"
ALBUM_ID_2 = "00000000-0000-0000-0000-000000000102"
ALBUM_ID_3 = "00000000-0000-0000-0000-000000000103"


def dump_alias(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True)
    return model.dict(by_alias=True)


def make_candidate(album_id=ALBUM_ID_1, similarity=0.9423, **overrides):
    values = {
        "album_id": album_id,
        "album_title": "Kind of Blue",
        "artist_name": "Miles Davis",
        "review_summary": "차분한 모달 재즈와 넓은 공간감이 돋보이는 앨범",
        "review_content": "modal jazz, cool, spacious mood",
        "review_url": "https://example.com/review",
        "similarity": similarity,
    }
    values.update(overrides)
    return SimpleNamespace(**values)

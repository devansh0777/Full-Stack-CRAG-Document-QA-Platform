from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer


EMBEDDING_DIMENSION = 384


@lru_cache
def get_embedding_model() -> HashingVectorizer:
    return HashingVectorizer(
        n_features=EMBEDDING_DIMENSION,
        alternate_sign=False,
        norm="l2",
    )


def _to_dense_rows(matrix) -> list[list[float]]:
    return matrix.astype(np.float32).toarray().tolist()


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return _to_dense_rows(model.transform([text]))[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return _to_dense_rows(model.transform(texts))

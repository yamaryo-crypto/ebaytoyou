"""画像ハッシュ: SHA-256 と perceptual hash（複数アルゴリズム）。"""
import hashlib
import io
from typing import Optional, Tuple

import PIL.Image

# ハッシュ計算前に正規化するサイズ。異なる解像度でも同一と判定しやすくする。
_NORMALIZE_SIZE = (256, 256)


def sha256_hex(data: bytes) -> str:
    """バイト列の SHA-256 を16進文字列で返す。"""
    return hashlib.sha256(data).hexdigest()


def _normalize_image(img: PIL.Image.Image) -> PIL.Image.Image:
    """ハッシュ計算用に画像を正規化。サイズ差があっても比較できるようにする。"""
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img.resize(_NORMALIZE_SIZE, PIL.Image.Resampling.LANCZOS)


def _load_normalized(data: bytes) -> Optional[PIL.Image.Image]:
    """画像を読み込み正規化して返す。失敗時は None。"""
    try:
        img = PIL.Image.open(io.BytesIO(data))
        return _normalize_image(img)
    except Exception:
        return None


def phash_image(data: bytes) -> Optional[object]:
    """
    画像の perceptual hash を返す。
    事前に正規化サイズへリサイズするため、相手がサイズ変更して投稿しても検知しやすい。
    失敗時は None。
    """
    try:
        import imagehash
        img = _load_normalized(data)
        if img is None:
            return None
        return imagehash.phash(img)
    except Exception:
        return None


def ahash_image(data: bytes) -> Optional[object]:
    """
    画像の average hash を返す。
    リサイズ・圧縮変化に比較的強い。pHash で拾えなかった場合の補助として利用。
    失敗時は None。
    """
    try:
        import imagehash
        img = _load_normalized(data)
        if img is None:
            return None
        return imagehash.average_hash(img)
    except Exception:
        return None


def dhash_image(data: bytes) -> Optional[object]:
    """
    画像の difference hash を返す。
    リサイズ・スケーリング変化に強い。リサイズ流用検知の補強用。
    失敗時は None。
    """
    try:
        import imagehash
        img = _load_normalized(data)
        if img is None:
            return None
        return imagehash.dhash(img)
    except Exception:
        return None


def phash_similar(h1: object, h2: object, threshold: int = 20) -> bool:
    """
    pHash の類似度。同一画像・リサイズ流用を検知。
    閾値は20に設定（誤検知を減らすため厳しく設定）。
    正しい検知の最大差分は32だが、誤検知の最小差分は20のため、より厳しい閾値が必要。
    """
    if h1 is None or h2 is None:
        return False
    try:
        diff = h1 - h2
        return int(diff) <= threshold
    except Exception:
        return False


def ahash_similar(h1: object, h2: object, threshold: int = 15) -> bool:
    """
    aHash の類似度。同一画像・リサイズ流用を検知。
    閾値は15に設定（誤検知を減らすため厳しく設定）。
    正しい検知の最大差分は28だが、誤検知の最小差分は15のため、より厳しい閾値が必要。
    """
    if h1 is None or h2 is None:
        return False
    try:
        diff = h1 - h2
        return int(diff) <= threshold
    except Exception:
        return False


def dhash_similar(h1: object, h2: object, threshold: int = 22) -> bool:
    """
    dHash の類似度。リサイズ流用を検知。
    閾値は22に設定（誤検知を減らすため厳しく設定）。
    正しい検知の最大差分は33だが、誤検知の最小差分は23のため、より厳しい閾値が必要。
    """
    if h1 is None or h2 is None:
        return False
    try:
        diff = h1 - h2
        return int(diff) <= threshold
    except Exception:
        return False


def perceptual_match(
    our_phash: object,
    their_phash: object,
    our_ahash: object,
    their_ahash: object,
    our_dhash: object = None,
    their_dhash: object = None,
    phash_threshold: int = 20,
    ahash_threshold: int = 15,
    dhash_threshold: int = 22,
) -> Tuple[bool, str]:
    """
    完全同一画像またはリサイズ・圧縮・品質変更された画像の流用を検知。
    精度向上のため、複数のハッシュの組み合わせで判定。
    閾値は誤検知を減らすため厳しく設定（pHash≤20, aHash≤15, dHash≤22）。
    """
    matches = []
    phash_match = phash_similar(our_phash, their_phash, threshold=phash_threshold)
    ahash_match = ahash_similar(our_ahash, their_ahash, threshold=ahash_threshold)
    dhash_match = False
    if our_dhash is not None and their_dhash is not None:
        dhash_match = dhash_similar(our_dhash, their_dhash, threshold=dhash_threshold)
    
    if phash_match:
        matches.append("phash")
    if ahash_match:
        matches.append("ahash")
    if dhash_match:
        matches.append("dhash")
    
    # 複数のハッシュが一致する場合（2つ以上）はマッチ
    if len(matches) >= 2:
        # phash+dhash のみの2-wayは誤検知が多いため厳格化。phash≤15, dhash≤18を要求
        if set(matches) == {"phash", "dhash"}:
            if phash_similar(our_phash, their_phash, threshold=15) and dhash_similar(
                our_dhash, their_dhash, threshold=18
            ):
                return True, "phash+dhash"
            return False, ""
        # ahash+dhash は phash が大きく乖離していると誤検知が多い（ID366, 369, 371, 374, 377, 379, 400）。
        # phash が類似（≤20）であることを要求（誤検知低減のため厳格化：25→20）
        if set(matches) == {"ahash", "dhash"}:
            if our_phash is not None and their_phash is not None:
                if not phash_similar(our_phash, their_phash, threshold=20):
                    return False, ""  # phash が大きく異なる＝別画像の可能性
            return True, "ahash+dhash"
        # phash+ahash は dhash が大きく乖離していると誤検知（ID373, 391, 395）。dhash が類似（≤15）であることを要求（誤検知低減のため厳格化：20→15）
        if set(matches) == {"phash", "ahash"}:
            if our_dhash is not None and their_dhash is not None:
                if not dhash_similar(our_dhash, their_dhash, threshold=15):
                    return False, ""  # dhash が大きく異なる＝別画像の可能性
            return True, "phash+ahash"
        return True, "+".join(matches)
    
    # 単独ハッシュは誤検知が多いため無効化（ahash: ID297, dhash: ID190など）
    if len(matches) == 1:
        return False, ""
    
    # relaxed パスは誤検知が圧倒的に多いため完全に削除（合っているものだけ検知する方針）
    return False, ""

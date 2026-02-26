from __future__ import annotations

import base64
import json
import unicodedata
from typing import Any

# If you're using Pydantic v2, BaseModel is pydantic.BaseModel
from pydantic import BaseModel


# Small helpers
def _is_probably_binary(b: bytes, threshold: float = 0.30) -> bool:
    """Heuristic: if many bytes are outside printable ASCII range (and not common whitespace),
    or if a null byte exists, consider it binary."""
    if not b:
        return False
    if b.find(b"\x00") != -1:
        return True
    # count bytes <= 8 or between 0x0E..0x1F or >=0x80 as 'suspicious'
    suspicious = 0
    for x in b:
        if x <= 0x08 or (0x0E <= x <= 0x1F) or x >= 0x80:
            suspicious += 1
    return (suspicious / len(b)) >= threshold


# Known magic signatures (first few bytes -> format name)
_MAGIC_SIGNATURES = {
    b"\x89PNG": "PNG image",
    b"%PDF": "PDF document",
    b"\xff\xd8\xff": "JPEG image",
    b"PK\x03\x04": "ZIP / Office document",
    b"GIF8": "GIF image",
    b"\x1f\x8b": "gzip compressed",
}


def _detect_magic(b: bytes) -> str | None:
    for sig, name in _MAGIC_SIGNATURES.items():
        if b.startswith(sig):
            return name
    return None


# Reuse stricter cleaning from prior answer (surrogates, non-characters, control handling)
_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF
_NONCHAR_RANGES = [(0xFDD0, 0xFDEF)]


def _is_noncharacter(cp: int) -> bool:
    if any(start <= cp <= end for start, end in _NONCHAR_RANGES):
        return True
    if (cp & 0xFFFF) in (0xFFFE, 0xFFFF):
        return True
    return False


def sanitize_utf8(
    text: str | bytes,
    *,
    placeholder: str = "\ufffd",
    remove_control_chars: bool = True,
    keep_whitespace_controls: bool = True,
    normalize: bool = True,
    try_fallback_encodings: bool = True,
    allow_binary_to_text: bool = True,  # if True, returns base64 for binary inputs
) -> str:
    """
    Robust sanitizer: returns a UTF-8-safe Python str, or raises ValueError for binary inputs
    unless allow_binary_to_text=True (in which case base64 text is returned).

    If `try_fallback_encodings` is True, attempts several decodings (utf-8-sig, utf-16, latin-1, cp1252)
    before falling back to replacement decoding.

    Raises
    ------
    ValueError
        If input is binary and allow_binary_to_text is False.
    """
    # Step A: get bytes if needed and detect binary
    if isinstance(text, str):
        s = text
        # We'll still normalize/clean below.
    else:
        # it's bytes-like
        b = bytes(text)
        # Detect magic signatures
        magic = _detect_magic(b)
        if magic:
            msg = f"Input appears to be binary ({magic}); not decodable as UTF-8."
            if allow_binary_to_text:
                # return base64 representation so downstream can safely carry it as text
                return base64.b64encode(b).decode("ascii")
            raise ValueError(msg)

        # Heuristic binary test
        if _is_probably_binary(b):
            if allow_binary_to_text:
                return base64.b64encode(b).decode("ascii")
            raise ValueError(
                "Input bytes look like binary (null bytes / high non-text byte ratio). "
                "If this is actually text, set try_fallback_encodings=True to attempt other decodings, "
                "or set allow_binary_to_text=True to get a base64 representation."
            )

        # Try decoding
        decode_errors = []
        if try_fallback_encodings:
            encodings_to_try = ["utf-8", "utf-8-sig", "utf-16", "latin-1", "cp1252"]
        else:
            encodings_to_try = ["utf-8"]

        s = None
        for enc in encodings_to_try:
            try:
                s = b.decode(enc, errors="strict")
                break
            except UnicodeDecodeError as e:
                decode_errors.append((enc, e))
        if s is None:
            # none decoded strictly; fall back to replacement decode using utf-8
            s = b.decode("utf-8", errors="replace")

    # Now s is a str; clean it
    if normalize:
        s = unicodedata.normalize("NFC", s)

    # strip BOMs at start (if any sneaked in)
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff")

    out_chars = []
    for ch in s:
        cp = ord(ch)
        # surrogates
        if _SURROGATE_MIN <= cp <= _SURROGATE_MAX:
            out_chars.append(placeholder)
            continue
        # non-characters
        if _is_noncharacter(cp):
            out_chars.append(placeholder)
            continue
        # control chars
        if remove_control_chars and cp <= 0x1F:
            if keep_whitespace_controls and ch in ("\t", "\n", "\r"):
                out_chars.append(ch)
            else:
                out_chars.append(placeholder)
            continue
        if remove_control_chars and cp == 0x7F:
            out_chars.append(placeholder)
            continue
        if cp > 0x10FFFF:
            out_chars.append(placeholder)
            continue
        out_chars.append(ch)

    cleaned = "".join(out_chars)
    if normalize:
        cleaned = unicodedata.normalize("NFC", cleaned)

    # final verification
    try:
        cleaned.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        cleaned = cleaned.encode("utf-8", errors="replace").decode(
            "utf-8", errors="replace"
        )

    return cleaned


# ---------------------------
# Sanitizer utilities
# ---------------------------
def _is_bytes_like(x: Any) -> bool:
    return isinstance(x, (bytes, bytearray))


def _bytes_to_base64_str(b: bytes) -> str:
    """Return an ASCII base64 encoding safe for JSON."""
    return base64.b64encode(b).decode("ascii")


def _try_decode_utf8(b: bytes) -> str | None:
    """Try strict utf-8 decode, return str on success else None."""
    try:
        return b.decode("utf-8", errors="strict")
    except Exception:
        return None


def _sanitize_structure(
    obj: Any,
    *,
    convert_bytes_to_base64: bool = True,
    allow_replacement_decode: bool = False,
) -> Any:
    """
    Recursively convert nested bytes/bytearray into either:
      - decoded UTF-8 string if valid utf-8
      - or base64 ascii string (default) if convert_bytes_to_base64=True
    Other containers (list/tuple/set/dict) are walked recursively.
    """
    # Bytes-like
    if _is_bytes_like(obj):
        raw = bytes(obj)
        # Prefer returning text if it's valid UTF-8
        decoded = _try_decode_utf8(raw)
        if decoded is not None:
            return decoded
        if allow_replacement_decode:
            # best-effort decode with replacement characters
            return raw.decode("utf-8", errors="replace")
        if convert_bytes_to_base64:
            return _bytes_to_base64_str(raw)
        # Fail-fast if caller doesn't want conversion
        raise ValueError(
            "Found binary bytes in structure and convert_bytes_to_base64=False"
        )

    # dict -> sanitize values
    if isinstance(obj, dict):
        return {
            k: _sanitize_structure(
                v,
                convert_bytes_to_base64=convert_bytes_to_base64,
                allow_replacement_decode=allow_replacement_decode,
            )
            for k, v in obj.items()
        }

    # list/tuple -> sanitize elements
    if isinstance(obj, list):
        return [
            _sanitize_structure(
                v,
                convert_bytes_to_base64=convert_bytes_to_base64,
                allow_replacement_decode=allow_replacement_decode,
            )
            for v in obj
        ]
    if isinstance(obj, tuple):
        return tuple(
            _sanitize_structure(
                v,
                convert_bytes_to_base64=convert_bytes_to_base64,
                allow_replacement_decode=allow_replacement_decode,
            )
            for v in obj
        )
    if isinstance(obj, set):
        return {
            _sanitize_structure(
                v,
                convert_bytes_to_base64=convert_bytes_to_base64,
                allow_replacement_decode=allow_replacement_decode,
            )
            for v in obj
        }

    # otherwise return as-is (str, int, float, None, etc.)
    return obj


# ---------------------------
# Mixin / override implementation
# ---------------------------
class _SanitizingModelMixin(BaseModel):
    """
    Mixin to override model_dump and model_dump_json to sanitize nested bytes.
    Inherit this before BaseModel or use as a sibling base:
        class CatOnSteroidsObservation(_SanitizingModelMixin, BaseModel):
            ...
    """

    def model_dump(
        self,
        *args,
        convert_bytes_to_base64: bool = True,
        allow_replacement_decode: bool = False,
        **kwargs,
    ) -> Any:
        """
        Override: call BaseModel.model_dump(...) then sanitize the returned Python structure.

        Extra keywords:
          - convert_bytes_to_base64: if True, convert discovered bytes -> base64 ascii str.
          - allow_replacement_decode: if True, attempt utf-8 decode with replacement before base64.
        """
        # Obtain the raw python structure from Pydantic
        raw = super().model_dump(*args, **kwargs)
        # Sanitize recursively
        sanitized = _sanitize_structure(
            raw,
            convert_bytes_to_base64=convert_bytes_to_base64,
            allow_replacement_decode=allow_replacement_decode,
        )
        return sanitized

    def model_dump_json(
        self,
        *args,
        convert_bytes_to_base64: bool = True,
        allow_replacement_decode: bool = False,
        **kwargs,
    ) -> str:
        """
        Override: produce a JSON string from a sanitized model dump.

        We call our model_dump() to get a sanitized python object and then json.dumps it.
        This avoids Pydantic's internal JSON conversion from attempting to coerce bytes to text.
        Extra keywords same as in model_dump.
        """
        # Use our sanitized model_dump to get a safe python object
        sanitized_obj = self.model_dump(
            *args,
            convert_bytes_to_base64=convert_bytes_to_base64,
            allow_replacement_decode=allow_replacement_decode,
            **kwargs,
        )
        # Now do JSON dump. Use ensure_ascii=False so unicode is preserved, but it's still UTF-8
        return json.dumps(sanitized_obj, ensure_ascii=False)


# ---------------------------
# Example: apply to your class
# ---------------------------
# If CatOnSteroidsObservation currently inherits from Observation (which itself inherits BaseModel),
# a safe approach is to create a new class that mixes-in the sanitizer before the existing base:
#
# class CatOnSteroidsObservation(_SanitizingModelMixin, Observation):
#     ...
#
# This ensures our overrides are used (method resolution order prefers mixin before Observation).
#
# Alternatively, if you want to patch the class directly, make CatOnSteroidsObservation inherit
# from _SanitizingModelMixin as the first base class.

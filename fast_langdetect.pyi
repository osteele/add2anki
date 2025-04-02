from typing import TypedDict

class LangDetectResult(TypedDict):
    lang: str
    score: float

class LangDetectConfig:
    def __init__(
        self,
        cache_dir: str | None = None,
        custom_model_path: str | None = None,
        proxy: str | None = None,
        allow_fallback: bool = True,
        disable_verify: bool = False,
        verify_hash: str | None = None,
        normalize_input: bool = True,
    ) -> None: ...
    def detect(self, text: str, *, low_memory: bool = True) -> LangDetectResult: ...
    def detect_multilingual(
        self,
        text: str,
        *,
        low_memory: bool = True,
        k: int = 5,
        threshold: float = 0.0,
    ) -> list[LangDetectResult]: ...

def detect(
    text: str,
    *,
    low_memory: bool = True,
    model_download_proxy: str | None = None,
    use_strict_mode: bool = False,
    config: LangDetectConfig | None = None,
) -> LangDetectResult: ...
def detect_multilingual(
    text: str,
    *,
    low_memory: bool = True,
    k: int = 5,
    threshold: float = 0.0,
    model_download_proxy: str | None = None,
    use_strict_mode: bool = False,
    config: LangDetectConfig | None = None,
) -> list[LangDetectResult]: ...
def detect_language(
    text: str,
    *,
    low_memory: bool = True,
) -> str: ...

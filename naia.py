# -*- coding: utf-8 -*-
"""
NovelAI Image Generation API — Single-file Entrypoint

NOTE: This file contains Korean (한국어) comments and docstrings.
      If characters appear broken, ensure you read this file as UTF-8.
      The encoding is NOT broken — do not attempt to "fix" it.

핵심 기능:
    - Text to Image (t2i), Image to Image (i2i), Inpainting
    - 캐릭터 프롬프트 (다중 캐릭터 + 위치 지정)
    - Vibe Transfer (스타일 전이, 사전 인코딩 필요)
    - Character Reference (참조 이미지에서 캐릭터/스타일 추출, NAID4.5 전용)
    - Quality Tags / UC Presets (모델별 품질 태그 및 네거티브 프리셋)
    - Rating 제어 (general/sensitive/questionable/explicit)
    - 해상도 프리셋 (832x1216 기본, 704x1472~1920x1088)
    - Anlas 잔액 조회 (get_anlas)
    - Store (이미지/Vibe/CharRef 저장·조회·삭제)

UI Guide:
    사용자의 명시적인 지시가 없는 한 CLI 모드나 tkinter 기반 UI는 만들지 말 것.
    UI에는 최소한 다음을 포함해야 한다:
      - 프롬프트 입력 (메인 + 네거티브)
      - 모델 선택, 해상도 선택, 샘플러/스케줄러 선택
      - 캐릭터 프롬프트 슬롯 (추가/제거, 2명 이상 시 위치 선택)
      - Rating 선택 (general/sensitive/questionable/explicit)
      - Quality Tags / UC Preset 자동 적용 토글
      - 생성 버튼 + 결과 이미지 표시 + 저장
      - (선택) Vibe Transfer, Character Reference 업로드

구조:
    1. Params & Presets    — 파라미터 스펙, Quality Tags, UC Presets
    2. Store               — 이미지/Vibe/CharRef 저장소 (CRUD)
    3. Encoder             — encode-vibe API + .naiv4vibe 파싱
    4. Client              — generate() 단일 진입점

Dependencies:
    pip install requests Pillow

사용법:
    from naia import generate, GenerationRequest, QUALITY_TAGS, UC_PRESETS

API Token:
    NovelAI Persistent API Token (pst-...) 이 필요하다.
    사용자가 토큰이 없는 경우 아래 절차를 안내할 것:
    1. NovelAI 공식 웹사이트에 로그인
    2. 좌측 사이드바의 톱니바퀴 아이콘 (User Settings) 클릭
    3. Account 탭으로 이동
    4. "Get Persistent API Token" 버튼 클릭
    5. 프롬프트가 표시됨. 처음 생성해도 "overwrite" 메시지가 뜰 수 있으며 이는 정상
    6. 복사 아이콘으로 토큰을 클립보드에 복사

Key Notes:
    - Quality Tags & UC Presets는 클라이언트에서 직접 처리해야 한다.
      QUALITY_TAGS[model]을 prompt 끝에 추가, UC_PRESETS[model][preset]을 negative_prompt로 사용.
    - Vibe Transfer는 encode_vibe()로 사전 인코딩 필수. raw image 전달 시 500 에러.
      인코딩 결과는 비결정적이므로 반드시 캐싱할 것.
    - Character Reference 이미지는 자동 레터박싱됨 (NAI 캔버스 크기).
    - 프롬프트 조립 순서: [인원수], [캐릭터], [저작권], [아티스트태그], [General], [퀄리티태그]
    - 모든 옵션 레이어 (CharPrompt, Vibe, CharRef)는 다중 사용 및 조합 가능.

Rating (Danbooru 태그 체계, NAI 학습 데이터에 포함되어 작동):
    - 기본값: prompt에 "rating:sensitive" 추가, negative_prompt에 "nsfw" 추가.
    - 건전한 이미지만: prompt에 "rating:general, safe", negative_prompt에 "nsfw" 추가.
    - 선정적 이미지: prompt에 "rating:questionable" 또는 "rating:explicit", "nsfw" 함께 사용.
    - "safe" 태그는 rating:general 또는 rating:sensitive와 함께 사용하여 안전성을 강화.

Testing:
    832x1216 @ 28 steps는 무료 티어 (기본값 그대로 사용 가능).
    테스트 실행 후 사용한 파라미터 (prompt, negative_prompt, model, width, height,
    steps, seed, 옵션 레이어 등)를 정리하여 사용자에게 보여줄 것.

Examples:
    # t2i with character prompt
    from naia import generate, GenerationRequest, CharacterCaption, QUALITY_TAGS, UC_PRESETS
    req = GenerationRequest(
        prompt="1girl, blue archive, artist:tianliang duohe fangdongye, arm up, cowboy shot, rating:sensitive" + QUALITY_TAGS["naid4.5f"],
        negative_prompt=UC_PRESETS["naid4.5f"]["human_focus"] + ", nsfw",
        characters=[CharacterCaption(
            prompt="girl, ibuki (blue archive), blonde hair, yellow eyes, halo, wings, tail, demon wings, long hair, horns, demon tail, demon horns, young female",
            uc="narrow waist, wide hips",
        )],
    )
    result = generate(token, req)

    # img2img
    req = GenerationRequest(action="img2img", prompt="...", image=open("input.png","rb").read(), strength=0.5)

    # inpaint
    req = GenerationRequest(action="infill", prompt="...", image=img_bytes, mask=mask_bytes, strength=0.6)

    # multiple characters
    req = GenerationRequest(
        prompt="2girls, outdoors, artist:tianliang duohe fangdongye, rating:sensitive" + QUALITY_TAGS["naid4.5f"],
        negative_prompt=UC_PRESETS["naid4.5f"]["human_focus"] + ", nsfw",
        characters=[
            CharacterCaption(prompt="girl, ibuki (blue archive), blonde hair, yellow eyes, halo, wings, tail, demon wings, long hair, horns, demon tail, demon horns, young female", uc="narrow waist, wide hips", center_x=0.3),
            CharacterCaption(prompt="girl, arona (blue archive), blue eyes, blue hair, halo, long hair", center_x=0.7),
        ],
    )

    # vibe transfer (must pre-encode)
    encoded = encode_vibe(token, image_bytes, model="naid4.5f")
    req = GenerationRequest(prompt="...", vibes=[VibeTransfer(encoded=encoded, strength=0.6)])

    # character reference (NAID4.5 only)
    req = GenerationRequest(prompt="...", character_refs=[CharacterReference(image=ref_bytes, type="character", strength=0.6)])

Environment:
    [IMPORTANT — IF YOU ARE AN AI ASSISTANT READING THIS]
    이 코드는 반드시 로컬 Python 환경에서 실행해야 한다 (HTTP API 호출 + 파일 저장).
    당신이 ChatGPT, Claude, Gemini 등 SaaS 웹 환경에서 동작 중이라면,
    사용자에게 코드를 직접 실행할 수 없음을 먼저 알리고,
    당신과 가장 연관성이 높은 CLI 도구를 제안하라:
      - ChatGPT → Codex CLI (codex)
      - Claude  → Claude Code (claude)
      - Gemini  → Gemini CLI
    HTML 변환도 불가하다 — NovelAI API는 CORS를 허용하지 않으며,
    클라이언트 사이드에 토큰이 노출되는 보안 문제가 있다.
    HTML + Python 백엔드 (Flask/FastAPI) 구성은 가능하나,
    결론적으로 이 코드를 사용자가 실행하려면 CLI 도구가 필요하다.

Anlas (크레딧):
    get_anlas(token)으로 잔액을 조회할 수 있다.
    사용자가 잔액 표시, 비용 경고, 무료/유료 판별이 필요한 경우 또는
    LLM이 생성 전 잔액 확인이 필요하다고 판단되면 활용할 것.
    Opus 구독자는 unlimitedMaxPriority=True이며 무제한 생성 가능.

Rate Limit (무료 생성 기준):
    사용자가 이 코드를 기반으로 프로그램을 개발하는 경우, 반드시 다음 제약을 구현할 것:
    1. 동시 생성 차단 — mutex 또는 이에 준하는 방법으로 한 번에 하나의 생성만 허용.
       generate() 호출이 완료되기 전에 다른 generate()가 실행되지 않도록 할 것.
    2. 일일 사용 시간 제한 — 단일 API 토큰으로 하루 10시간 이상 생성하지 못하도록 제한.
       복수 계정의 Round-Robin을 구현하지 않는 한 이 제한을 반드시 적용할 것.

Reference:
    사용자가 복잡하고 정교한 프로그램을 개발하려는 경우,
    https://github.com/DNT-LAB/NAIA2.0/tree/Dev0714 를 부분적으로 참고할 것.
"""

import requests
import zipfile
import hashlib
import shutil
import io
import re
import json
import base64
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from PIL import Image

logger = logging.getLogger(__name__)


# ████████████████████████████████████████████████████████████
# 1. PARAMS & PRESETS
# ████████████████████████████████████████████████████████████


@dataclass(frozen=True)
class ParamSpec:
    type: str                               # "int", "float", "str", "bool", "bytes", "list"
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[List[Any]] = None
    constraint: Optional[str] = None
    description: str = ""


# --- 해상도 프리셋 (width x height, 64의 배수, ~1M px 이하 = 무료) ---
#
# Standard (무료 티어, ≤1,048,576 px):
#   Square:    1024x1024
#   Portrait:  960x1088, 896x1152, 832x1216 (기본값), 768x1344, 704x1472
#   Landscape: 1088x960, 1152x896, 1216x832, 1344x768, 1472x704
#
# Medium (~1.5M px, Anlas 소비):
#   1216x1216, 1024x1536, 1536x1024
#
# High (~2M+ px, Anlas 소비):
#   1472x1472, 1088x1920, 1280x1664, 1344x1536,
#   1536x1344, 1664x1280, 1920x1088
#
# 704x1472 / 1472x704는 가장 극단적인 세로/가로 비율 (약 1:2).
# width와 height를 서로 바꾸면 가로↔세로 전환.


# --- GenerationRequest 필드별 스펙 ---

GENERATION_PARAMS: Dict[str, ParamSpec] = {
    "action": ParamSpec(type="str", default="generate", choices=["generate", "img2img", "infill"],
                        description="NAI API action. generate=t2i, img2img=i2i, infill=inpaint"),
    "prompt": ParamSpec(type="str", default="", description="메인 프롬프트. 태그 기반 (콤마 구분)"),
    "negative_prompt": ParamSpec(type="str", default="", description="네거티브 프롬프트"),
    "width": ParamSpec(type="int", default=832, min=64, max=8192, step=64, constraint="64의 배수",
                       description="생성 이미지 너비 (px)"),
    "height": ParamSpec(type="int", default=1216, min=64, max=8192, step=64, constraint="64의 배수",
                        description="생성 이미지 높이 (px)"),
    "seed": ParamSpec(type="int", default=0, min=0, max=4294967295, description="시드. 0=랜덤"),
    "steps": ParamSpec(type="int", default=28, min=1, max=150, step=1, description="샘플링 스텝 수"),
    "cfg_scale": ParamSpec(type="float", default=5.0, min=0.0, max=30.0, step=0.1,
                           description="CFG Scale. 프롬프트 충실도"),
    "cfg_rescale": ParamSpec(type="float", default=0.4, min=0.0, max=1.0, step=0.05,
                             description="CFG Rescale. 과채도 보정"),
    "sampler": ParamSpec(type="str", default="k_euler_ancestral",
                         choices=["k_euler", "k_euler_ancestral", "k_dpmpp_2m", "k_dpmpp_2s_ancestral",
                                  "k_dpmpp_sde", "k_dpmpp_2m_sde", "ddim_v3"],
                         description="샘플러"),
    "scheduler": ParamSpec(type="str", default="native",
                           choices=["karras", "native", "exponential", "polyexponential"],
                           description="노이즈 스케줄러"),
    "model": ParamSpec(type="str", default="naid4.5f",
                       choices=["naid4.5f", "naid4.5c", "naid4f", "naid4c", "naid3"],
                       description="모델 약칭"),
    "var_plus": ParamSpec(type="bool", default=False,
                          description="VAR+. skip_cfg_above_sigma 활성화 (CharRef 사용 시 자동 비활성화)"),
    "image": ParamSpec(type="bytes", default=None, description="입력 이미지 (i2i, inpaint). None이면 t2i"),
    "strength": ParamSpec(type="float", default=0.5, min=0.01, max=0.99, step=0.01,
                          description="디노이즈 강도 (i2i/inpaint)"),
    "noise": ParamSpec(type="float", default=0.05, min=0.0, max=0.99, step=0.01,
                       description="추가 노이즈 (i2i 전용)"),
    "mask": ParamSpec(type="bytes", default=None, constraint="원본의 1/8 크기",
                      description="인페인트 마스크. None이면 inpaint 아님"),
}

CHARACTER_CAPTION_PARAMS: Dict[str, ParamSpec] = {
    "prompt": ParamSpec(type="str", default="", description="캐릭터별 프롬프트 (태그)"),
    "uc": ParamSpec(type="str", default="", description="캐릭터별 네거티브"),
    "center_x": ParamSpec(type="float", default=0.5, min=0.1, max=0.9, step=0.2,
                          constraint="5x5 그리드: A=0.1, B=0.3, C=0.5, D=0.7, E=0.9. 캐릭터 1명이면 무조건 0.5",
                          description="캐릭터 X 위치 힌트. 2명 이상일 때만 조작 가능"),
    "center_y": ParamSpec(type="float", default=0.5, min=0.1, max=0.9, step=0.2,
                          constraint="5x5 그리드: 1=0.1, 2=0.3, 3=0.5, 4=0.7, 5=0.9. 캐릭터 1명이면 무조건 0.5",
                          description="캐릭터 Y 위치 힌트. 2명 이상일 때만 조작 가능"),
}

VIBE_TRANSFER_PARAMS: Dict[str, ParamSpec] = {
    "encoded": ParamSpec(type="str", default=None,
                         constraint="encode_vibe()의 결과. raw image 불가",
                         description="사전 인코딩된 vibe 데이터 (base64)"),
    "strength": ParamSpec(type="float", default=0.6, min=0.01, max=1.0, step=0.01,
                          description="Vibe 적용 강도"),
    "information_extracted": ParamSpec(type="float", default=1.0, min=0.01, max=1.0, step=0.01,
                                      description="정보 추출량. 낮을수록 고주파 디테일 손실"),
}

CHARACTER_REFERENCE_PARAMS: Dict[str, ParamSpec] = {
    "image": ParamSpec(type="bytes", default=None,
                       constraint="자동 레터박싱 (1024x1536/1536x1024/1472x1472)",
                       description="참조 이미지. NAID4.5 전용"),
    "type": ParamSpec(type="str", default="character&style",
                      choices=["character", "style", "character&style"],
                      description="추출 모드: 캐릭터/스타일/둘 다"),
    "strength": ParamSpec(type="float", default=0.6, min=0.0, max=1.0, step=0.01,
                          description="참조 적용 강도"),
    "fidelity": ParamSpec(type="float", default=1.0, min=0.0, max=1.0, step=0.01,
                          constraint="API에서 1.0 - fidelity로 변환 (secondary_strength)",
                          description="충실도. 높을수록 참조에 강하게 따름"),
}


# --- 프롬프트 조립 순서 (NAI 공식 태그 전개 방식) ---
#
# [인원수], [캐릭터], [저작권], [아티스트태그], [General Prompts], [퀄리티태그]
#
# 예: "1girl, hatsune miku, vocaloid, artist:tianliang duohe fangdongye, smile, outdoor, location, very aesthetic, masterpiece, no text"

PROMPT_ORDER = ["person_count", "character", "copyright", "artist", "general", "quality"]


# --- Quality Tags (품질 제어, 프롬프트에 직접 삽입) ---
#
# best quality > amazing quality > great quality > normal quality > bad quality > worst quality
# 프롬프트에 넣으면 품질 향상, 네거티브에 넣으면 해당 품질 억제.
# QUALITY_TAGS 프리셋에 이미 모델별 권장 조합이 포함되어 있음.
#
# --- Furry (V4 이상) ---
#
# "fur dataset" 태그를 프롬프트 앞에 추가하면 furry 스타일로 전환.
# 이 태그가 있으면 태그 체계가 furry 전용으로 바뀜.
#
# --- Renamed Tags (파이프 문자 충돌 회피) ---
#
# NAI에서 | 는 프롬프트 믹싱 구분자이므로, 아래 태그는 이름이 변경됨:
#   v → peace sign,  double v → double peace,  |_| → bar eyes,
#   ||/ → open \m/,  :| → neutral face,  ;| → neutral face,
#   <|> <|> → neco-arc eyes,  eyepatch bikini → square bikini,
#   tachi-e → character image


# --- 프롬프트 가중치 문법 ---
#
# NAID4 / NAID4.5 (새 문법):
#   강조:  1.1::tag::          → tag에 1.1배 가중치
#   약화:  0.8::tag::          → tag에 0.8배 가중치
#   복수:  0.8::tag1, tag2::   → 묶어서 가중치 적용
#   예:    1.2::smile::, 0.8::feet::, -0.5::blush, sweat::
#   음수 가중치(-) 가능: 해당 요소를 억제
#
# NAID3 (구 문법):
#   강조:  {tag} → 1.05배, {{tag}} → 1.05^2배
#   약화:  [tag] → 0.95배, [[tag]] → 0.95^2배
#   혼합:  [tag1, tag2] → 두 태그 사이를 혼합


# --- Quality Tags 프리셋 (모델별, 프롬프트 끝에 추가) ---

QUALITY_TAGS = {
    "naid4.5f": ", location, very aesthetic, masterpiece, no text",
    "naid4.5c": ", location, masterpiece, no text, -0.8::feet::, rating:general",
    "naid4f":   ", no text, best quality, very aesthetic, absurdres",
    "naid4c":   ", rating:general, amazing quality, very aesthetic, absurdres",
    "naid3":    ", best quality, amazing quality, very aesthetic, absurdres",
}


# --- UC (Undesired Content) 프리셋 (클라이언트가 negative_prompt에 직접 추가) ---

UC_PRESETS = {
    "naid4.5f": {
        "heavy": "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page",
        "light": "lowres, artistic error, scan artifacts, worst quality, bad quality, jpeg artifacts, multiple views, very displeasing, too many watermarks, negative space, blank page",
        "human_focus": "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page, @_@, mismatched pupils, glowing eyes, bad anatomy",
        "none": "",
    },
    "naid4.5c": {
        "heavy": "blurry, lowres, upscaled, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, halftone, multiple views, logo, too many watermarks, negative space, blank page",
        "light": "blurry, lowres, upscaled, artistic error, scan artifacts, jpeg artifacts, logo, too many watermarks, negative space, blank page",
        "human_focus": "blurry, lowres, upscaled, artistic error, film grain, scan artifacts, bad anatomy, bad hands, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, halftone, multiple views, logo, too many watermarks, @_@, mismatched pupils, glowing eyes, negative space, blank page",
        "none": "",
    },
    "naid4f": {
        "heavy": "blurry, lowres, error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, multiple views, logo, too many watermarks",
        "light": "blurry, lowres, error, worst quality, bad quality, jpeg artifacts, very displeasing",
        "none": "",
    },
    "naid4c": {
        "heavy": "blurry, lowres, error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, logo, dated, signature, multiple views, gigantic breasts",
        "light": "blurry, lowres, error, worst quality, bad quality, jpeg artifacts, very displeasing, logo, dated, signature",
        "none": "",
    },
    "naid3": {
        "heavy": "lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract]",
        "light": "lowres, jpeg artifacts, worst quality, watermark, blurry, very displeasing",
        "human_focus": "lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract], bad anatomy, bad hands, @_@, mismatched pupils, heart-shaped pupils, glowing eyes",
        "none": "",
    },
}


def validate(params: dict, spec: Dict[str, ParamSpec]) -> List[str]:
    """파라미터 유효성 검사. 위반 사항 목록 반환 (빈 리스트면 통과)."""
    errors = []
    for key, value in params.items():
        if key not in spec:
            continue
        s = spec[key]
        if s.choices and value not in s.choices:
            errors.append(f"{key}: {value!r} not in {s.choices}")
        if s.min is not None and isinstance(value, (int, float)):
            if value < s.min:
                errors.append(f"{key}: {value} < min({s.min})")
        if s.max is not None and isinstance(value, (int, float)):
            if value > s.max:
                errors.append(f"{key}: {value} > max({s.max})")
        if s.constraint and "배수" in s.constraint and isinstance(value, int):
            m = re.search(r"(\d+)의 배수", s.constraint)
            if m and value % int(m.group(1)) != 0:
                errors.append(f"{key}: {value} is not a multiple of {m.group(1)}")
    return errors


# ████████████████████████████████████████████████████████████
# 2. STORE
# ████████████████████████████████████████████████████████████


# --- 공통 ---

_CANVASES = [(2 / 3, 1024, 1536), (3 / 2, 1536, 1024), (1 / 1, 1472, 1472)]

def _sha256_16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _letterbox(image_bytes: bytes) -> bytes:
    """이미지를 NAI 캔버스 크기로 레터박싱."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img)
        img = bg
    else:
        img = img.convert("RGB")

    w, h = img.size
    ratio = w / h
    _, cw, ch = min(_CANVASES, key=lambda c: abs(ratio - c[0]))

    if w / cw > h / ch:
        nw, nh = cw, int(h * (cw / w))
    else:
        nh, nw = ch, int(w * (ch / h))

    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (cw, ch), (0, 0, 0))
    canvas.paste(resized, ((cw - nw) // 2, (ch - nh) // 2))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# --- image_store: save/{datetime}/{number}.png ---

class image_store:
    BASE_DIR = Path("save")

    @staticmethod
    def save(raw_bytes: bytes, session: Optional[str] = None) -> Path:
        """생성 이미지를 저장. raw_bytes 그대로 써서 NAI 메타데이터 보존."""
        if session:
            d = image_store.BASE_DIR / session
        else:
            d = image_store.BASE_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
        d.mkdir(parents=True, exist_ok=True)
        existing = [int(f.stem) for f in d.glob("*.png") if f.stem.isdigit()]
        num = max(existing, default=0) + 1
        path = d / f"{num:05d}.png"
        path.write_bytes(raw_bytes)
        return path

    @staticmethod
    def list_sessions() -> List[str]:
        if not image_store.BASE_DIR.exists():
            return []
        return sorted([d.name for d in image_store.BASE_DIR.iterdir()
                       if d.is_dir() and len(d.name) == 15 and d.name[8] == "_"], reverse=True)

    @staticmethod
    def list_images(session: str) -> List[Path]:
        d = image_store.BASE_DIR / session
        return sorted(d.glob("*.png"), key=lambda p: p.stem) if d.exists() else []

    @staticmethod
    def delete_image(session: str, filename: str) -> bool:
        path = image_store.BASE_DIR / session / filename
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def delete_session(session: str) -> bool:
        d = image_store.BASE_DIR / session
        if d.exists():
            shutil.rmtree(d)
            return True
        return False


# --- vibe_store: save/vibe_transfer/{model}/{hash}.json ---

class vibe_store:
    BASE_DIR = Path("save/vibe_transfer")
    MODEL_FOLDER_MAP = {
        "nai-diffusion-4-5-full": "NAID4.5F",
        "nai-diffusion-4-5-curated": "NAID4.5C",
        "nai-diffusion-4-full": "NAID4.0F",
        "nai-diffusion-4-curated-preview": "NAID4.0C",
    }

    @staticmethod
    def _model_path(model: str) -> Path:
        """모델 디렉터리 경로 반환 (생성하지 않음)."""
        folder = vibe_store.MODEL_FOLDER_MAP.get(model, model)
        return vibe_store.BASE_DIR / folder

    @staticmethod
    def _model_dir(model: str) -> Path:
        """모델 디렉터리 경로 반환 + 생성 (쓰기 전용)."""
        d = vibe_store._model_path(model)
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def save_encoding(image_bytes: bytes, encoded: str, model: str,
                      information_extracted: float = 1.0) -> str:
        file_hash = _sha256_16(image_bytes)
        model_dir = vibe_store._model_dir(model)
        json_path = model_dir / f"{file_hash}.json"

        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"file_hash": file_hash, "encodings": {}}

        data["encodings"][str(information_extracted)] = encoded
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 썸네일
        images_dir = model_dir / "images"
        images_dir.mkdir(exist_ok=True)
        thumb_path = images_dir / f"{file_hash}.png"
        if not thumb_path.exists():
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            w, h = img.size
            if w > h:
                nw, nh = 386, int(h * (386 / w))
            else:
                nh, nw = 386, int(w * (386 / h))
            img.resize((nw, nh), Image.LANCZOS).save(thumb_path, "PNG")

        return file_hash

    @staticmethod
    def get_encoding(file_hash: str, model: str,
                     information_extracted: float = 1.0) -> Optional[str]:
        json_path = vibe_store._model_path(model) / f"{file_hash}.json"
        if not json_path.exists():
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        encodings = data.get("encodings", {})
        if not encodings:
            return None
        closest_key = min(encodings.keys(), key=lambda k: abs(float(k) - information_extracted))
        return encodings[closest_key]

    @staticmethod
    def list_vibes(model: str) -> List[Dict]:
        model_dir = vibe_store._model_path(model)
        if not model_dir.exists():
            return []
        result = []
        for jf in sorted(model_dir.glob("*.json")):
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            ie_values = [float(k) for k in data.get("encodings", {}).keys()]
            thumb = model_dir / "images" / f"{data['file_hash']}.png"
            result.append({"file_hash": data["file_hash"], "ie_values": ie_values,
                           "thumbnail": str(thumb) if thumb.exists() else None})
        return result

    @staticmethod
    def delete_vibe(file_hash: str, model: Optional[str] = None) -> int:
        count = 0
        if model:
            model_dir = vibe_store._model_path(model)
            dirs = [model_dir] if model_dir.exists() else []
        elif vibe_store.BASE_DIR.exists():
            dirs = [d for d in vibe_store.BASE_DIR.iterdir() if d.is_dir()]
        else:
            return 0
        for d in dirs:
            for path in [d / f"{file_hash}.json", d / "images" / f"{file_hash}.png"]:
                if path.exists():
                    path.unlink()
                    count += 1
        return count


# --- ref_store: save/character_reference/{hash}.png + letterboxed/ ---

class ref_store:
    BASE_DIR = Path("save/character_reference")
    LETTERBOX_DIR = BASE_DIR / "letterboxed"

    @staticmethod
    def save(image_bytes: bytes) -> str:
        ref_store.BASE_DIR.mkdir(parents=True, exist_ok=True)
        ref_store.LETTERBOX_DIR.mkdir(parents=True, exist_ok=True)
        file_hash = _sha256_16(image_bytes)

        orig_path = ref_store.BASE_DIR / f"{file_hash}.png"
        if not orig_path.exists():
            orig_path.write_bytes(image_bytes)

        lb_path = ref_store.LETTERBOX_DIR / f"{file_hash}.png"
        if not lb_path.exists():
            lb_path.write_bytes(_letterbox(image_bytes))

        return file_hash

    @staticmethod
    def get_letterboxed(file_hash: str) -> Optional[bytes]:
        lb_path = ref_store.LETTERBOX_DIR / f"{file_hash}.png"
        return lb_path.read_bytes() if lb_path.exists() else None

    @staticmethod
    def get_original(file_hash: str) -> Optional[bytes]:
        orig_path = ref_store.BASE_DIR / f"{file_hash}.png"
        return orig_path.read_bytes() if orig_path.exists() else None

    @staticmethod
    def list_refs() -> List[dict]:
        if not ref_store.BASE_DIR.exists():
            return []
        return [{"file_hash": f.stem, "path": str(f),
                 "has_letterbox": (ref_store.LETTERBOX_DIR / f"{f.stem}.png").exists()}
                for f in sorted(ref_store.BASE_DIR.glob("*.png"))]

    @staticmethod
    def delete(file_hash: str) -> bool:
        deleted = False
        for path in [ref_store.BASE_DIR / f"{file_hash}.png",
                     ref_store.LETTERBOX_DIR / f"{file_hash}.png"]:
            if path.exists():
                path.unlink()
                deleted = True
        return deleted


# ████████████████████████████████████████████████████████████
# 3. ENCODER
# ████████████████████████████████████████████████████████████

ENCODE_URL = "https://image.novelai.net/ai/encode-vibe"

VIBE_MODEL_MAP = {
    "v4-5full": "nai-diffusion-4-5-full",
    "v4-5curated": "nai-diffusion-4-5-curated",
    "v4full": "nai-diffusion-4-full",
    "v4curated": "nai-diffusion-4-curated-preview",
}
VIBE_MODEL_MAP_REVERSE = {v: k for k, v in VIBE_MODEL_MAP.items()}


@dataclass
class VibeEncoding:
    """단일 인코딩 결과."""
    encoded: str
    information_extracted: float
    model: str


@dataclass
class VibeData:
    """.naiv4vibe 파일 하나에 대응하는 데이터."""
    id: str = ""
    encodings: Dict[str, Dict[float, str]] = field(default_factory=dict)
    image_b64: Optional[str] = None

    def get_encoding(self, model: str, ie: float = 1.0) -> Optional[str]:
        model_key = VIBE_MODEL_MAP_REVERSE.get(model, model)
        model_encodings = self.encodings.get(model_key)
        if not model_encodings:
            return None
        closest_ie = min(model_encodings.keys(), key=lambda k: abs(k - ie))
        return model_encodings[closest_ie]


def encode_vibe(token: str, image: bytes, model: str = "nai-diffusion-4-5-full",
                information_extracted: float = 1.0, max_retries: int = 3) -> str:
    """이미지를 vibe 데이터로 인코딩. 결과는 비결정적이므로 반드시 저장하여 재사용."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"image": base64.b64encode(image).decode(),
               "information_extracted": information_extracted, "model": model}

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(ENCODE_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code in (502, 503, 504, 520):
                time.sleep(2 * attempt)
                last_error = f"HTTP {resp.status_code}"
                continue
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode()
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            if attempt < max_retries:
                time.sleep(1)
                continue
            break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(1)
                continue
            break
    raise RuntimeError(f"encode-vibe failed after {max_retries} retries: {last_error}")


def load_vibe_file(path: str) -> List[VibeData]:
    """.naiv4vibe 또는 .naiv4vibebundle 파일을 로드."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("identifier") == "novelai-vibe-transfer-bundle":
        return [_parse_single_vibe(v) for v in data.get("vibes", [])
                if v.get("identifier") == "novelai-vibe-transfer"]
    elif data.get("identifier") == "novelai-vibe-transfer":
        return [_parse_single_vibe(data)]
    else:
        raise ValueError(f"Unknown vibe file format: {data.get('identifier')}")


def save_vibe_file(path: str, vibes: List[VibeData]) -> None:
    """VibeData를 .naiv4vibe 또는 .naiv4vibebundle로 저장."""
    if len(vibes) == 1:
        data = _serialize_single_vibe(vibes[0])
    else:
        data = {"identifier": "novelai-vibe-transfer-bundle", "version": 1,
                "vibes": [_serialize_single_vibe(v) for v in vibes]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _parse_single_vibe(data: dict) -> VibeData:
    vibe = VibeData(id=data.get("id", ""), image_b64=data.get("image"))
    for model_key, model_encodings in data.get("encodings", {}).items():
        if model_key not in VIBE_MODEL_MAP:
            continue
        vibe.encodings[model_key] = {}
        for _enc_id, enc_info in model_encodings.items():
            if isinstance(enc_info, dict):
                ie = enc_info.get("params", {}).get("information_extracted", 1.0)
                encoding = enc_info.get("encoding")
                if encoding:
                    vibe.encodings[model_key][float(ie)] = encoding
    return vibe


def _serialize_single_vibe(vibe: VibeData) -> dict:
    encodings = {}
    for model_key, ie_map in vibe.encodings.items():
        encodings[model_key] = {}
        for ie, encoded in ie_map.items():
            encodings[model_key][f"ie_{ie}"] = {
                "encoding": encoded, "params": {"information_extracted": ie}}
    data = {"identifier": "novelai-vibe-transfer", "version": 1, "type": "encoding",
            "id": vibe.id, "encodings": encodings}
    if vibe.image_b64:
        data["image"] = vibe.image_b64
    return data


# ████████████████████████████████████████████████████████████
# 4. CLIENT
# ████████████████████████████████████████████████████████████

API_URL = "https://image.novelai.net/ai/generate-image"

MODELS = {
    "naid4.5f": "nai-diffusion-4-5-full",
    "naid4.5c": "nai-diffusion-4-5-curated",
    "naid4f":   "nai-diffusion-4-full",
    "naid4c":   "nai-diffusion-4-curated-preview",
    "naid3":    "nai-diffusion-3",
}


# --- 스키마 ---

@dataclass
class CharacterCaption:
    """V4+ 캐릭터 프롬프트. 위치 좌표와 함께 메인 프롬프트에 조합된다."""
    prompt: str
    uc: str = ""
    center_x: float = 0.5
    center_y: float = 0.5


@dataclass
class VibeTransfer:
    """인코딩된 vibe 데이터로 스타일을 전이. encoded는 encode_vibe()의 결과."""
    encoded: str
    strength: float = 0.6
    information_extracted: float = 1.0


@dataclass
class CharacterReference:
    """NAID4.5 전용. 참조 이미지에서 캐릭터/스타일을 추출.
    type: "character" | "style" | "character&style" (기본)"""
    image: bytes
    type: Literal["character", "style", "character&style"] = "character&style"
    strength: float = 0.6
    fidelity: float = 1.0


@dataclass
class GenerationRequest:
    """NAI API 생성 요청 스키마.
    빈 리스트/None 필드는 해당 기능 미사용으로 처리된다.
    파라미터 범위/타입은 GENERATION_PARAMS 참조."""

    action: Literal["generate", "img2img", "infill"] = "generate"
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 832
    height: int = 1216
    seed: int = 0
    steps: int = 28
    cfg_scale: float = 5.0
    cfg_rescale: float = 0.4
    sampler: str = "k_euler_ancestral"
    scheduler: str = "native"
    model: str = "naid4.5f"
    var_plus: bool = False

    image: Optional[bytes] = None
    strength: float = 0.5
    noise: float = 0.05
    mask: Optional[bytes] = None

    characters: List[CharacterCaption] = field(default_factory=list)
    vibes: List[VibeTransfer] = field(default_factory=list)
    character_refs: List[CharacterReference] = field(default_factory=list)


@dataclass
class GenerationResult:
    image: Image.Image
    raw_bytes: bytes


# --- 내부: 페이로드 빌드 ---

def _resolve_model(key: str, is_inpaint: bool = False) -> str:
    name = MODELS.get(key.lower(), key)
    if is_inpaint:
        name += "-inpainting"
    return name


def _build_base_parameters(r: GenerationRequest) -> dict:
    model_name = _resolve_model(r.model)
    params = {
        "width": r.width, "height": r.height, "n_samples": 1,
        "seed": r.seed, "extra_noise_seed": r.seed,
        "sampler": r.sampler, "steps": r.steps, "scale": r.cfg_scale,
        "negative_prompt": r.negative_prompt, "cfg_rescale": r.cfg_rescale,
        "noise_schedule": r.scheduler,
        "params_version": 3, "legacy": False, "legacy_v3_extend": False,
    }

    if r.var_plus:
        params["skip_cfg_above_sigma"] = 58 if "4-5" in model_name else 19
    else:
        params["skip_cfg_above_sigma"] = None

    if "nai-diffusion-4" in model_name:
        params.update(_build_v4_prompt(r))
    if r.vibes:
        _apply_vibe_transfer(params, r.vibes)
    if r.character_refs:
        if "4-5" not in model_name:
            raise ValueError(f"Character Reference is only supported on NAID4.5 models, got '{r.model}'")
        _apply_character_reference(params, r.character_refs)

    return params


def _build_v4_prompt(r: GenerationRequest) -> dict:
    char_captions, neg_char_captions = [], []
    for c in r.characters:
        center = {"x": c.center_x, "y": c.center_y}
        char_captions.append({"char_caption": c.prompt, "centers": [center]})
        neg_char_captions.append({"char_caption": c.uc, "centers": [center]})

    return {
        "autoSmea": True, "prefer_brownian": True, "ucPreset": 0,
        "use_coords": False, "legacy_uc": False, "add_original_image": True,
        "v4_prompt": {
            "caption": {"base_caption": r.prompt, "char_captions": char_captions},
            "use_coords": False, "use_order": True,
        },
        "v4_negative_prompt": {
            "caption": {"base_caption": r.negative_prompt, "char_captions": neg_char_captions},
            "legacy_uc": False,
        },
    }


def _apply_vibe_transfer(params: dict, vibes: List[VibeTransfer]) -> None:
    params["reference_image_multiple"] = [v.encoded for v in vibes]
    params["reference_strength_multiple"] = [v.strength for v in vibes]
    params["reference_information_extracted_multiple"] = [v.information_extracted for v in vibes]
    params["normalize_reference_strength_multiple"] = True


def _apply_character_reference(params: dict, refs: List[CharacterReference]) -> None:
    params["director_reference_images"] = [
        base64.b64encode(_letterbox(r.image)).decode() for r in refs]
    params["director_reference_strength_values"] = [r.strength for r in refs]
    params["director_reference_secondary_strength_values"] = [1.0 - r.fidelity for r in refs]
    params["director_reference_descriptions"] = [
        {"caption": {"base_caption": r.type, "char_captions": []}, "legacy_uc": False}
        for r in refs]
    params["director_reference_information_extracted"] = [1.0] * len(refs)
    params["controlnet_strength"] = 1.0
    params["inpaintImg2ImgStrength"] = 1.0
    params["normalize_reference_strength_multiple"] = True
    params.pop("skip_cfg_above_sigma", None)


def _encode_mask(mask_bytes: bytes, scale: int = 8) -> str:
    img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    img = img.point(lambda x: 255 if x > 128 else 0, "1")
    w, h = img.size
    img = img.resize((w * scale, h * scale), Image.NEAREST).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# --- 내부: HTTP ---

def _post(token: str, payload: dict, max_retries: int = 3) -> bytes:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=180)
            if resp.status_code == 401:
                raise RuntimeError("Authentication failed (401). Check your API token.")
            if resp.status_code == 429:
                raise RuntimeError("Rate limited (429). Wait before retrying.")
            if resp.status_code in (502, 503, 504, 520):
                time.sleep(2 * attempt)
                last_error = f"HTTP {resp.status_code}"
                continue
            resp.raise_for_status()
            return resp.content
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            if attempt < max_retries:
                time.sleep(1)
                continue
            break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(1)
                continue
            break
    raise RuntimeError(f"API call failed after {max_retries} retries: {last_error}")


def _unzip_image(content: bytes) -> GenerationResult:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        image_bytes = zf.read(zf.infolist()[0])
    return GenerationResult(image=Image.open(io.BytesIO(image_bytes)), raw_bytes=image_bytes)


# --- Public API ---

def get_anlas(token: str) -> dict:
    """Anlas(크레딧) 잔액 조회.
    Returns: {"fixed": int, "purchased": int, "total": int, "opus": bool}
    프로그램 개발 시 무료/유료 생성 판별, 잔액 표시, 비용 경고 등에 활용할 수 있다.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get("https://api.novelai.net/user/subscription", headers=headers, timeout=10)
        if resp.status_code == 401:
            raise RuntimeError("Authentication failed (401). Check your API token.")
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Anlas query failed: HTTP {e.response.status_code}") from e
    except Exception as e:
        raise RuntimeError(f"Anlas query failed: {e}") from e
    data = resp.json()
    steps = data.get("trainingStepsLeft", {})
    fixed = steps.get("fixedTrainingStepsLeft", 0)
    purchased = steps.get("purchasedTrainingSteps", 0)
    opus = data.get("perks", {}).get("unlimitedMaxPriority", False)
    return {"fixed": fixed, "purchased": purchased, "total": fixed + purchased, "opus": opus}


def generate(token: str, req: GenerationRequest) -> GenerationResult:
    """GenerationRequest를 받아 이미지를 생성한다."""
    # 캐릭터 1명이면 좌표 강제 0.5, 0.5
    if len(req.characters) == 1:
        c = req.characters[0]
        if c.center_x != 0.5 or c.center_y != 0.5:
            req.characters[0] = CharacterCaption(
                prompt=c.prompt, uc=c.uc, center_x=0.5, center_y=0.5)

    errors = validate({
        "action": req.action, "width": req.width, "height": req.height,
        "steps": req.steps, "cfg_scale": req.cfg_scale, "cfg_rescale": req.cfg_rescale,
        "sampler": req.sampler, "scheduler": req.scheduler, "model": req.model,
        "strength": req.strength, "noise": req.noise,
    }, GENERATION_PARAMS)
    for i, c in enumerate(req.characters):
        errors += [f"characters[{i}].{e}" for e in validate(
            {"center_x": c.center_x, "center_y": c.center_y}, CHARACTER_CAPTION_PARAMS)]
    for i, v in enumerate(req.vibes):
        errors += [f"vibes[{i}].{e}" for e in validate(
            {"strength": v.strength, "information_extracted": v.information_extracted}, VIBE_TRANSFER_PARAMS)]
    for i, r_ in enumerate(req.character_refs):
        errors += [f"character_refs[{i}].{e}" for e in validate(
            {"type": r_.type, "strength": r_.strength, "fidelity": r_.fidelity}, CHARACTER_REFERENCE_PARAMS)]
    if errors:
        raise ValueError(f"Invalid parameters: {'; '.join(errors)}")

    if req.action == "generate":
        return _generate_t2i(token, req)
    elif req.action == "img2img":
        if req.image is None:
            raise ValueError("img2img requires 'image'")
        return _generate_i2i(token, req)
    elif req.action == "infill":
        if req.image is None or req.mask is None:
            raise ValueError("infill requires 'image' and 'mask'")
        return _generate_inpaint(token, req)
    else:
        raise ValueError(f"Unknown action: {req.action}")


def _generate_t2i(token: str, r: GenerationRequest) -> GenerationResult:
    payload = {"input": r.prompt, "model": _resolve_model(r.model),
               "action": "generate", "parameters": _build_base_parameters(r)}
    return _unzip_image(_post(token, payload))


def _generate_i2i(token: str, r: GenerationRequest) -> GenerationResult:
    params = _build_base_parameters(r)
    params["image"] = base64.b64encode(r.image).decode()
    params["strength"] = r.strength
    params["noise"] = r.noise
    payload = {"input": r.prompt, "model": _resolve_model(r.model),
               "action": "img2img", "parameters": params}
    return _unzip_image(_post(token, payload))


def _generate_inpaint(token: str, r: GenerationRequest) -> GenerationResult:
    params = _build_base_parameters(r)
    params.update({"image": base64.b64encode(r.image).decode(), "mask": _encode_mask(r.mask),
                   "add_original_image": True, "inpaintImg2ImgStrength": r.strength,
                   "noise": 0, "deliberate_euler_ancestral_bug": False,
                   "controlnet_strength": 1, "request_type": "NativeInfillingRequest"})
    payload = {"input": r.prompt, "model": _resolve_model(r.model, is_inpaint=True),
               "action": "infill", "parameters": params}
    return _unzip_image(_post(token, payload))

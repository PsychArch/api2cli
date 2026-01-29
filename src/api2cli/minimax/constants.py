"""Constants for Minimax API integration."""

from __future__ import annotations

API_BASE_URL = "https://api.minimaxi.com/v1"

ENDPOINTS = {
    "IMAGE_GENERATION": "/image_generation",
    "TEXT_TO_SPEECH": "/t2a_v2",
}

DEFAULT_HEADERS = {
    "MM-API-Source": "api2cli",
}

DEFAULT_TIMEOUT_SECONDS = 30

# Rate limit constants are not enforced in sync CLI, but kept for reference.
RATE_LIMITS = {
    "IMAGE": {"rpm": 10, "burst": 3},
    "TTS": {"rpm": 20, "burst": 5},
}

IMAGE_CONSTRAINTS = {
    "PROMPT_MAX_LENGTH": 1500,
    "MIN_DIMENSION": 512,
    "MAX_DIMENSION": 2048,
    "DIMENSION_STEP": 8,
    "ASPECT_RATIOS": [
        "1:1",
        "16:9",
        "4:3",
        "3:2",
        "2:3",
        "3:4",
        "9:16",
        "21:9",
    ],
    "STYLE_TYPES": ["漫画", "元气", "中世纪", "水彩"],
    "STYLE_WEIGHT_MIN": 0.01,
    "STYLE_WEIGHT_MAX": 1.0,
}

TTS_CONSTRAINTS = {
    "TEXT_MAX_LENGTH": 10000,
    "SPEED_MIN": 0.5,
    "SPEED_MAX": 2.0,
    "VOLUME_MIN": 0.1,
    "VOLUME_MAX": 10.0,
    "PITCH_MIN": -12,
    "PITCH_MAX": 12,
    "EMOTIONS": ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"],
    "FORMATS": ["mp3", "wav", "flac", "pcm"],
    "SAMPLE_RATES": [8000, 16000, 22050, 24000, 32000, 44100],
    "BITRATES": [64000, 96000, 128000, 160000, 192000, 224000, 256000, 320000],
    "VOICE_MODIFY_INTENSITY_MIN": -100,
    "VOICE_MODIFY_INTENSITY_MAX": 100,
    "VOICE_MODIFY_TIMBRE_MIN": -100,
    "VOICE_MODIFY_TIMBRE_MAX": 100,
    "SOUND_EFFECTS": ["spacious_echo", "auditorium_echo", "lofi_telephone", "robotic"],
}

DEFAULTS = {
    "IMAGE": {
        "aspect_ratio": "1:1",
        "style_weight": 0.8,
    },
    "TTS": {
        "voice_id": "female-shaonv",
        "speed": 1.0,
        "volume": 1.0,
        "pitch": 0.0,
        "emotion": "neutral",
        "format": "mp3",
        "sample_rate": 32000,
        "bitrate": 128000,
        "channel": 1,
    },
}

VOICE_IDS = [
    "male-qn-qingse",
    "male-qn-jingying",
    "male-qn-badao",
    "male-qn-daxuesheng",
    "female-shaonv",
    "female-yujie",
    "female-chengshu",
    "female-tianmei",
    "presenter_male",
    "presenter_female",
    "audiobook_male_1",
    "audiobook_male_2",
    "audiobook_female_1",
    "audiobook_female_2",
    "male-qn-qingse-jingpin",
    "male-qn-jingying-jingpin",
    "male-qn-badao-jingpin",
    "male-qn-daxuesheng-jingpin",
    "female-shaonv-jingpin",
    "female-yujie-jingpin",
    "female-chengshu-jingpin",
    "female-tianmei-jingpin",
    "clever_boy",
    "cute_boy",
    "lovely_girl",
    "cartoon_pig",
    "bingjiao_didi",
    "junlang_nanyou",
    "chunzhen_xuedi",
    "lengdan_xiongzhang",
    "badao_shaoye",
    "tianxin_xiaoling",
    "qiaopi_mengmei",
    "wumei_yujie",
    "diadia_xuemei",
    "danya_xuejie",
    "Santa_Claus",
    "Grinch",
    "Rudolph",
    "Arnold",
    "Charming_Santa",
    "Charming_Lady",
    "Sweet_Girl",
    "Cute_Elf",
    "Attractive_Girl",
    "Serene_Woman",
]

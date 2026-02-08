from __future__ import annotations

# 保存する value（将来の実行エンジンが参照する識別子）

INPUT_FORMATS: list[tuple[str, str]] = [
    ("free_text", "自由記述（テキスト）"),
    ("bullet_points", "箇条書き"),
    ("json", "JSON"),
    ("url_list", "URL一覧"),
    ("slack_thread_url", "SlackスレッドURL"),
]

OUTPUT_FORMATS: list[tuple[str, str]] = [
    ("plain_text", "テキスト（平文）"),
    ("markdown", "Markdown"),
    ("json", "JSON"),
    ("marp_markdown", "Marp Markdown（スライド）"),
    ("image_url", "画像URL（生成画像など）"),
]


def label_for_input(value: str) -> str:
    for v, label in INPUT_FORMATS:
        if v == value:
            return label
    return value


def label_for_output(value: str) -> str:
    for v, label in OUTPUT_FORMATS:
        if v == value:
            return label
    return value


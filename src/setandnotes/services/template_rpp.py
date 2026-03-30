from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TemplateRpp:
    template_path: Path
    template_text: str

    @classmethod
    def load(cls, path: Path | str) -> "TemplateRpp":
        template_path = Path(path)
        return cls(template_path=template_path, template_text=template_path.read_text(encoding="utf-8"))

    def is_placeholder_template(self) -> bool:
        return "{{" in self.template_text and "}}" in self.template_text

    def render(
        self,
        *,
        song_long_name: str,
        project_offset: str,
        bpm: float,
        main_audio_path: str,
        tc_audio_path: str,
    ) -> str:
        rendered = self.template_text
        replacements = {
            "{{SONG_LONG_NAME}}": song_long_name,
            "{{PROJECT_OFFSET}}": project_offset,
            "{{BPM}}": str(bpm),
            "{{MAIN_AUDIO_PATH}}": main_audio_path,
            "{{TC_AUDIO_PATH}}": tc_audio_path,
        }
        for token, value in replacements.items():
            rendered = rendered.replace(token, value)
        return rendered

    def render_reaper_project(
        self,
        *,
        project_offset_seconds: float,
        bpm: float,
        track_media_path: str,
        tc_media_path: str,
        track_length_seconds: float,
        tc_length_seconds: float,
        track_name: str,
        tc_name: str,
        tc_entry_offset_seconds: float | None = None,
        multicam_video_path: str | None = None,
        wide_video_path: str | None = None,
        multicam_length_seconds: float | None = None,
        wide_length_seconds: float | None = None,
        multicam_name: str = "",
        wide_name: str = "",
    ) -> str:
        if self.is_placeholder_template():
            return self.render(
                song_long_name=track_name,
                project_offset=f"{project_offset_seconds}",
                bpm=bpm,
                main_audio_path=track_media_path,
                tc_audio_path=tc_media_path,
            )

        root, _ = _parse_reaper_block(self.template_text.splitlines())
        _set_top_level_value(root, "PROJOFFS", f"{project_offset_seconds} 0 0")
        base_tempo_bpm = _top_level_tempo_bpm(root)
        if tc_entry_offset_seconds is not None and tc_entry_offset_seconds > 0:
            _set_top_level_value(root, "TEMPO", f"{base_tempo_bpm} 4 4 0")
            _replace_tempo_points(
                root,
                [
                    _tempo_point(0.0, base_tempo_bpm),
                    _tempo_point(tc_entry_offset_seconds, bpm),
                ],
            )
        else:
            _set_top_level_value(root, "TEMPO", f"{bpm} 4 4 0")
            _replace_tempo_points(root, [])

        _replace_track_items(root, "TRACK", _build_audio_item(track_name, track_media_path, track_length_seconds))
        _replace_track_items(root, "TC", _build_audio_item(tc_name, tc_media_path, tc_length_seconds))
        _replace_optional_track_item(
            root,
            "Video_Multicam",
            _build_media_item(multicam_name, multicam_video_path, multicam_length_seconds),
        )
        _replace_optional_track_item(
            root,
            "Video_Wide",
            _build_media_item(wide_name, wide_video_path, wide_length_seconds),
        )

        return "\n".join(_render_reaper_block(root))


@dataclass(slots=True)
class _ReaperNode:
    value: str | "_ReaperBlock"


@dataclass(slots=True)
class _ReaperBlock:
    header: str
    children: list[_ReaperNode]


def _parse_reaper_block(lines: list[str], start: int = 0) -> tuple[_ReaperBlock, int]:
    header = lines[start]
    children: list[_ReaperNode] = []
    index = start + 1

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == ">":
            return _ReaperBlock(header=header, children=children), index + 1
        if stripped.startswith("<") and stripped != ">":
            child, index = _parse_reaper_block(lines, index)
            children.append(_ReaperNode(child))
            continue
        children.append(_ReaperNode(line))
        index += 1

    raise ValueError("unbalanced REAPER template")


def _render_reaper_block(block: _ReaperBlock) -> list[str]:
    lines = [block.header]
    child_indent = _line_indent(block.header)
    for child in block.children:
        if isinstance(child.value, str):
            lines.append(child.value)
        else:
            lines.extend(_render_reaper_block(child.value))
    lines.append(f"{child_indent}>")
    return lines


def _line_indent(line: str) -> str:
    match = re.match(r"^\s*", line)
    return match.group(0) if match else ""


def _set_top_level_value(root: _ReaperBlock, key: str, value: str) -> None:
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s+)(.*)$")
    for index, child in enumerate(root.children):
        if not isinstance(child.value, str):
            continue
        match = pattern.match(child.value)
        if match:
            root.children[index] = _ReaperNode(f"{match.group(1)}{value}")
            return
    root.children.append(_ReaperNode(f"  {key} {value}"))


def _top_level_tempo_bpm(root: _ReaperBlock) -> float:
    pattern = re.compile(r"^\s*TEMPO\s+([0-9.]+)\b")
    for child in root.children:
        if not isinstance(child.value, str):
            continue
        match = pattern.match(child.value)
        if match:
            return float(match.group(1))
    return 120.0


def _replace_track_items(root: _ReaperBlock, track_name: str, item_block: _ReaperBlock) -> None:
    _replace_optional_track_item(root, track_name, item_block)


def _replace_optional_track_item(root: _ReaperBlock, track_name: str, item_block: _ReaperBlock | None) -> None:
    for child_index, child in enumerate(root.children):
        if not isinstance(child.value, _ReaperBlock):
            continue
        block = child.value
        if not block.header.strip().startswith("<TRACK "):
            continue
        if _track_name(block) != track_name:
            continue
        filtered_children = [
            node
            for node in block.children
            if not (isinstance(node.value, _ReaperBlock) and node.value.header.strip().startswith("<ITEM"))
        ]
        if item_block is not None:
            filtered_children.append(_ReaperNode(item_block))
        root.children[child_index] = _ReaperNode(_ReaperBlock(header=block.header, children=filtered_children))
        return


def _replace_tempo_points(root: _ReaperBlock, points: list[str]) -> None:
    for child_index, child in enumerate(root.children):
        if not isinstance(child.value, _ReaperBlock):
            continue
        block = child.value
        if not block.header.strip().startswith("<TEMPOENVEX"):
            continue
        filtered_children = [
            node
            for node in block.children
            if not (isinstance(node.value, str) and node.value.strip().startswith("PT "))
        ]
        filtered_children.extend(_ReaperNode(point) for point in points)
        root.children[child_index] = _ReaperNode(_ReaperBlock(header=block.header, children=filtered_children))
        return


def _tempo_point(position_seconds: float, bpm: float, numerator: int = 4, denominator: int = 4) -> str:
    signature = _time_signature_code(numerator, denominator)
    return f"    PT {position_seconds:.12f} {bpm:.10f} 1 {signature}"


def _time_signature_code(numerator: int, denominator: int) -> int:
    denominator_base = {
        1: 65536,
        2: 131072,
        4: 262144,
        8: 524288,
        16: 1048576,
        32: 2097152,
        64: 4194304,
        128: 8388608,
    }
    if denominator not in denominator_base:
        raise ValueError(f"unsupported time signature denominator: {denominator}")
    return denominator_base[denominator] + numerator


def _track_name(block: _ReaperBlock) -> str:
    for child in block.children:
        if isinstance(child.value, str):
            match = re.match(r'^\s*NAME\s+"?(.*?)"?\s*$', child.value)
            if match:
                return match.group(1)
    return ""


def _build_audio_item(item_name: str, media_path: str, length_seconds: float) -> _ReaperBlock:
    return _build_item(item_name, media_path, length_seconds, source_kind="WAVE")


def _build_media_item(item_name: str, media_path: str | None, length_seconds: float | None) -> _ReaperBlock | None:
    if not media_path or length_seconds is None:
        return None
    suffix = Path(media_path).suffix.lower()
    source_kind = "VIDEO" if suffix in {".mov", ".mp4", ".mkv", ".avi", ".mxf", ".webm"} else "WAVE"
    return _build_item(item_name, media_path, length_seconds, source_kind=source_kind)


def _build_item(item_name: str, media_path: str, length_seconds: float, *, source_kind: str) -> _ReaperBlock:
    indent = "    "
    source_indent = indent + "  "
    item_name = Path(media_path).name if item_name == "" else item_name
    source_block = _ReaperBlock(
        header=f"{source_indent}<SOURCE {source_kind}",
        children=[_ReaperNode(f'{source_indent}  FILE "Media/{Path(media_path).name}"')],
    )
    return _ReaperBlock(
        header=f"{indent}<ITEM",
        children=[
            _ReaperNode(f"{indent}  POSITION 0"),
            _ReaperNode(f"{indent}  SNAPOFFS 0"),
            _ReaperNode(f"{indent}  LENGTH {length_seconds}"),
            _ReaperNode(f"{indent}  LOOP 1"),
            _ReaperNode(f"{indent}  ALLTAKES 0"),
            _ReaperNode(f"{indent}  FADEIN 1 0 0 1 0 0 0"),
            _ReaperNode(f"{indent}  FADEOUT 1 0.01 0 1 0 0 0"),
            _ReaperNode(f"{indent}  MUTE 0 0"),
            _ReaperNode(f"{indent}  SEL 0"),
            _ReaperNode(f"{indent}  IGUID {{{uuid.uuid4()}}}"),
            _ReaperNode(f"{indent}  IID 1"),
            _ReaperNode(f'{indent}  NAME "{item_name}"'),
            _ReaperNode(f"{indent}  VOLPAN 1 0 1 -1"),
            _ReaperNode(f"{indent}  SOFFS 0"),
            _ReaperNode(f"{indent}  PLAYRATE 1 1 0 -1 0 0.0025"),
            _ReaperNode(f"{indent}  CHANMODE 0"),
            _ReaperNode(f"{indent}  GUID {{{uuid.uuid4()}}}"),
            _ReaperNode(source_block),
        ],
    )

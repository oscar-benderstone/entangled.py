from dataclasses import dataclass, field
from pathlib import Path, PurePath

import mawk
import re

from .document import ReferenceId, TextLocation, ReferenceMap
from .errors.user import IndentationError
from .hooks.base import HookBase


@dataclass
class Frame:
    ref: ReferenceId
    indent: str
    content: list[str] = field(default_factory=list)


class CodeReader(mawk.RuleSet):
    """Reads an annotated code file."""

    def __init__(self, path: PurePath, refs: ReferenceMap):
        self.location = TextLocation(path, 0)
        self.stack: list[Frame] = [Frame(ReferenceId("#root#", PurePath("-"), -1), "")]
        self.refs: ReferenceMap = refs

    @property
    def current(self) -> Frame:
        return self.stack[-1]

    @mawk.always
    def increase_line_number(self, _):
        self.location.line_number += 1

    @mawk.on_match(
        r"^(?P<indent>\s*).* ~/~ begin <<(?P<source>[^#<>]+)#(?P<ref_name>[^#<>]+)>>\[(?P<ref_count>init|\d+)\]"
    )
    def on_block_begin(self, m: re.Match):
        ref_name = m["ref_name"]

        # When there are lines above the first ref, say a shebang, swap
        # them into the first block.
        if len(self.stack) == 1 and len(self.stack[0].content) > 0:
            content = self.stack[0].content
            self.stack[0].content = []
        else:
            content = []

        if m["ref_count"] == "init":
            ref_count = 0
            if not m["indent"].startswith(self.current.indent):
                raise IndentationError(self.location)
            indent = m["indent"].removeprefix(self.current.indent)
            self.current.content.append(f"{indent}<<{ref_name}>>")
        else:
            ref_count = int(m["ref_count"])

        self.stack.append(
            Frame(
                ReferenceId(m["ref_name"], PurePath(m["source"]), ref_count),
                m["indent"],
                content,
            )
        )
        return []

    @mawk.on_match(r"^(?P<indent>\s*).* ~/~ end")
    def on_block_end(self, m: re.Match):
        if m["indent"] != self.current.indent:
            raise IndentationError(self.location)
        self.refs[self.current.ref].source = "\n".join(self.current.content)
        self.stack.pop()
        return []

    @mawk.always
    def otherwise(self, line: str):
        if line.strip() == "":
            self.current.content.append("")
            return []
        if not line.startswith(self.current.indent):
            raise IndentationError(self.location)
        self.current.content.append(line.removeprefix(self.current.indent))
        return []


def read_code_file(path: Path, refs: ReferenceMap):
    with open(path, "r") as f:
        CodeReader(path, refs).run(f.read())


# def read_code_file(
#     path: Path, refs: ReferenceMap | None = None, hooks: list[HookBase] | None = None
# ) -> tuple[ReferenceMap, list[Content]]:
#
#     with open(path, "r") as f:
#         rel_path = path.resolve().relative_to(Path.cwd())
#         return read_markdown_string(f.read(), rel_path, refs, hooks)

# def read_markdown_string(
#         text: str,
#         path_str: Path = Path("-"),
#         refs: ReferenceMap | None = None,
#         hooks: list[HookBase] | None = None) \
#         -> tuple[ReferenceMap, list[Content]]:
#     md = MarkdownLexer(path_str)
#     md.run(text)
#
#     hooks = hooks if hooks is not None else []
#     refs = refs if refs is not None else ReferenceMap()
#
#     def process(r: RawContent) -> Content:
#         match r:
#             case CodeBlock():
#                 for h in hooks: h.on_read(r)
#                 block_id = get_id(r.properties)
#                 target_file = get_attribute(r.properties, "file")
#
#                 if mode := get_attribute(r.properties, "mode"):
#                     r.mode = int(mode, 8)
#
#                 ref_name = block_id or target_file
#                 if ref_name is None:
#                     ref_name = f"unnamed-{r.origin}"
#                 ref = refs.new_id(r.origin.filename, ref_name)
#
#                 refs[ref] = r
#                 if target_file is not None:
#                     refs.targets.add(target_file)
#                 if target_file is not None and block_id is not None:
#                     refs.alias[target_file] = block_id
#
#                 return ref
#
#             case PlainText(): return r
#
#     content = list(map(process, md.raw_content))
#     logging.debug("found ids: %s", list(refs.map.keys()))
#     return refs, content

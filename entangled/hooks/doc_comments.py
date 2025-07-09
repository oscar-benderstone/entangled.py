from ..document import CodeBlock
from .base import HookBase
from ..logging import logger

log = logger()


class Hook(HookBase):
    def on_read(self, code: CodeBlock):
        if code.language is None:
            log.info("Failed to find language")
            return

        if code.language.doc_comment is None:
            log.info("Need an input DocComment")
            return

        # doc_comment = f"{code.language.doc_comment}|"
        # i = 0
        # while i < len(code.source):
        #     pass
        #
        # header = "\n".join(
        #     line[len(trigger) :]
        #     for line in code.source.splitlines()
        #     if line.startswith(trigger)
        # )

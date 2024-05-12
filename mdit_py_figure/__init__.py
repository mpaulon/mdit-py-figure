"""Process figures"""

from __future__ import annotations

import re
from string import digits
from typing import TYPE_CHECKING, List, Optional, Sequence

from markdown_it import MarkdownIt
from markdown_it.common.utils import isStrSpace, normalizeReference
from markdown_it.rules_block import StateBlock
from markdown_it.rules_core import StateCore
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

from mdit_py_plugins.utils import is_code_block

if TYPE_CHECKING:
    from markdown_it.renderer import RendererProtocol
    from markdown_it.utils import EnvType, OptionsDict


def figure_plugin(md: MarkdownIt) -> None:
    """Plugin ported from
    `markdown-it-figure <https://github.com/chromeos/static-site-scaffold-modules/tree/main/modules/markdown-it-figure>`
    """

    def parse_figure(state: StateInline, silent: bool) -> bool:
        figure_id = ""
        label = None
        href = ""
        oldPos = state.pos
        max = state.posMax
        alt = None

        pos = state.pos

        if state.src[pos] != "#":
            return False

        pos += 1

        while pos < state.posMax and state.src[pos] in digits:
            if figure_id is None:
                figure_id = ""
            figure_id += state.src[pos]
            pos += 1
        if state.src[pos] != "[":
            return False

        labelStart = pos + 1
        labelEnd = state.md.helpers.parseLinkLabel(state, pos, False)

        # parser failed to find ']', so it's not a valid link
        if labelEnd < 0:
            return False

        pos = labelEnd + 1

        if pos < max and state.src[pos] == "(":
            #
            # Inline link
            #

            # [caption](  <href>  [alt]  )
            #           ^^ skipping these spaces
            pos += 1
            while pos < max:
                ch = state.src[pos]
                if not isStrSpace(ch) and ch != "\n":
                    break
                pos += 1

            if pos >= max:
                return False

            # [caption](  <href>  [alt]  )
            #             ^^^^^^ parsing link destination
            start = pos
            res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax)
            if res.ok:
                href = state.md.normalizeLink(res.str)
                if state.md.validateLink(href):
                    pos = res.pos
                else:
                    href = ""

            # [caption](  <href>  [alt]  )
            #                   ^^ skipping these spaces
            start = pos
            while pos < max:
                ch = state.src[pos]
                if not isStrSpace(ch) and ch != "\n":
                    break
                pos += 1

            # [caption](  <href>  [alt]  )
            #                     ^^^^^ parsing alt text
            # FIXME
            if state.src[pos] == "[":
                alt_start = pos + 1
                alt_end = state.md.helpers.parseLinkLabel(state, pos, False)
                alt = state.src[alt_start:alt_end]
                pos = alt_end + 1
            if pos < max and start != pos:
                # [caption](  <href>  [alt]  )
                #                          ^^ skipping these spaces
                while pos < max:
                    ch = state.src[pos]
                    if not isStrSpace(ch) and ch != "\n":
                        break
                    pos += 1
            else:
                title = ""

            if pos >= max or state.src[pos] != ")":
                state.pos = oldPos
                return False

            pos += 1

        else:
            return False
        #
        # We found the end of the link, and know for a fact it's a valid link
        # so all that's left to do is to call tokenizer.
        #
        if not silent:
            content = state.src[labelStart:labelEnd]  # caption

            tokens: list[Token] = []
            state.md.inline.parse(content, state.md, state.env, tokens)  # parse caption

            token = state.push("figure", "fig", 0)
            token.attrs = {"src": href}
            token.children = tokens or None
            token.content = content

            if alt is not None:
                token.attrSet("alt", alt)

            if figure_id:
                token.meta["id"] = figure_id

        state.pos = pos
        state.posMax = max
        return True

    def render_figure(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ):
        token = tokens[idx]
        id_tag = ' id="figure-' + token.meta["id"] + '"' if token.meta.get("id") else ""
        return f'<figure{id_tag}><img{self.renderAttrs(token)}/><figcaption>{token.content}</figcaption></figure>'

        raise NotImplementedError()

    md.inline.ruler.before(
        "link", "figure_def", parse_figure, {"alt": ["paragraph", "reference"]}
    )

    md.add_render_rule("figure", render_figure)

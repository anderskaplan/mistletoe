from itertools import chain
import re
from typing import Iterable
from mistletoe import block_token, span_token


_whitespace = re.compile(r"\s+")

def wordwrap(token: block_token.BlockToken, max_line_length: int = 80) -> str:
    # TODO
    # iterate over the tree of block tokens
    # Paragraphs and SetextHeading are the only tokens with wrappable content
    # other blocks are just rendered as they are
    lines = _wrap(token.children, max_line_length=max_line_length)
    return "".join(lines)

def _wrap(tokens: list[span_token.SpanToken], max_line_length: int) -> Iterable[str]:
    particles = chain.from_iterable([token.flatten() for token in tokens])

    current_line = ""
    for word in _aggregate_words(particles):
        first = True
        for item in word.splitlines():
            if first:
                # first (or only) line: try to fit item on the current line.
                # if it doesn't fit, flush the current line and start on a new.
                first = False
                if not current_line:
                    current_line = item
                    continue
                
                test = current_line + " " + item
                if len(test) <= max_line_length:
                    current_line = test
                else:
                    yield current_line + "\n"
                    current_line = item
            else:
                # second..last row: flush the current line and start on a new.
                if current_line:
                    yield current_line + "\n"
                current_line = item

    if current_line:
        yield current_line

def _aggregate_words(particles: Iterable[span_token.Particle]) -> Iterable[str]:
    # note: "words" may contain line breaks, for example hard line breaks and inline code.
    word = ""
    for particle in particles:
        if isinstance(particle.token, span_token.InlineCode):
            word += particle.text
            continue
        if isinstance(particle.token, span_token.LineBreak) and not particle.token.soft:
            yield word + particle.text + "\n"
            word = ""
            continue
        
        first = True
        for item in _whitespace.split(particle.text):
            if first:
                word += item
                first = False
            else:
                if word:
                    yield word
                word = item

    if word:
        yield word

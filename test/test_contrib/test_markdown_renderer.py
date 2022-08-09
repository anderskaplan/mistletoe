from unittest import TestCase, mock
from contrib.markdown_renderer import MarkdownRenderer

from mistletoe.block_token import Document

class TestMarkdownRenderer(TestCase):
    def test_paragraphs_and_blank_lines(self):
        input = \
"""Paragraph 1. Single line. Followed by two white-space-only lines.

 
Paragraph 2. Two
lines, no final line break."""
        expected = \
"""Paragraph 1. Single line. Followed by two white-space-only lines.


Paragraph 2. Two
lines, no final line break.
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, expected)

    def test_line_breaks(self):
        input = \
"""soft line break 
hard line break\\
another hard line break  
that's all
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_span_tokens(self):
        input = \
"""_**emphasized and strong**_  \\*escaped\\*  `code span` ~~strikethrough~~ <h1>
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_images_and_links(self):
        input = \
"""[a link](#url (title))
[another link](<someplace> '*emphasized title*')
![an \\[*image*\\]](#url)
<http://foo.bar>
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_block_tokens(self):
        input = \
""" **  * ** * ** * **
## atx *heading* ##

setext
heading!
===============
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_roundtrip_readme(self):
        with open('README.md', 'r') as file:
            lines = file.readlines()
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(lines))
        self.assertEquals(lines, rendered)

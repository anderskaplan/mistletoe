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

    def test_thematic_break_and_headings(self):
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

    def test_numbered_list(self):
        input = \
"""
  22)  *yeah*
  96)
 128) here begins a nested list.
       + apples
       +  bananas
"""
        expected = \
"""
22) *yeah*
96) 
128) here begins a nested list.
     + apples
     + bananas
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, expected)

    def test_bulleted_list(self):
        input = \
"""
* **Fast**:
  mistletoe is the fastest implementation of CommonMark in Python.
  See the [performance][performance] section for details.

"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_code_blocks(self):
        input = \
"""
    this is an indented code block
      on two lines 
    with some extra whitespace here and there, to be preserved  
      just as it is.
```
now for a fenced code block 
  where indentation is also preserved. as are the double spaces at the end of this line:  
```
  ~~~this is an info string: behold the fenced code block with tildes!
  *tildes are great*
  ~~~
1. a list item with an embedded

       indented code block.
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_html_block(self):
        input = \
"""
<h1>mistletoe<img src='https://cdn.rawgit.com/miyuchina/mistletoe/master/resources/logo.svg' align='right' width='128' height='128'></h1>
<br>

+ <h1>mistletoe<img src='https://cdn.rawgit.com/miyuchina/mistletoe/master/resources/logo.svg' align='right' width='128' height='128'></h1>
  <br>
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_block_quote(self):
        input = \
"""
> a block quote
> > a nested block quote
> 1. > a list with a nested block quote
"""
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
        self.assertEquals(rendered, input)

    def test_roundtrip_readme(self):
        with open('README.md', 'r') as file:
            lines = file.readlines()
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(lines))
        with open('roundtrip.md', 'w') as outf:
            outf.write(rendered)
        self.assertEquals(lines, rendered)

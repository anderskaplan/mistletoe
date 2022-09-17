from unittest import TestCase

from contrib.markdown_renderer import MarkdownRenderer
from mistletoe.block_token import Document


class TestMarkdownRenderer(TestCase):
    @staticmethod
    def roundtrip(input):
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
            return rendered

    def test_empty_document(self):
        input = []
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_paragraphs_and_blank_lines(self):
        input = ['Paragraph 1. Single line. Followed by two white-space-only lines.\n',
                 '\n',
                 '\n',
                 'Paragraph 2. Two\n',
                 'lines, no final line break.']
        rendered = self.roundtrip(input)
        # note: a line break is always added at the end of a paragraph.
        self.assertEqual(rendered, "".join(input) + "\n")

    def test_soft_and_hard_line_breaks(self):
        input = ['soft line break\n',
                 'hard line break\\\n',
                 'another hard line break  \n',
                 'that\'s all.\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_emphasized_strong_and_strikethrough(self):
        input = ['_**emphasized and strong**_  ~~strikethrough~~\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_escaped_chars_and_html_span(self):
        input = ['misc span tokens:  \\*escaped, not emphasized\\*  <h1>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_code_span(self):
        input = ['a) `code span` b) ``trailing space `` c) ` leading and trailing space `\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_images_and_links(self):
        input = ['[a link](#url (title))\n',
                 '[another link](<url-in-angle-brackets> \'*emphasized\n',
                 'title*\')\n',
                 '![an \\[*image*\\], escapes and emphasis](#url "title")\n',
                 '<http://auto.link>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_thematic_break(self):
        input = [' **  * ** * ** * **\n',
                 'followed by a paragraph of text\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_headings(self):
        input = ['## atx *heading* ##\n',
                 '# another atx heading, without trailing hashes\n',
                 '###\n',
                 '^ empty atx heading\n',
                 '\n',
                 'setext\n',
                 'heading!\n',
                 '===============\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_numbered_list(self):
        input = ['  22)  *emphasized list item*\n',
                 '  96)\n',
                 ' 128) here begins a nested list.\n',
                 '       + apples\n',
                 '       +  bananas\n']
        xpect = ['22) *emphasized list item*\n',
                 '96) \n',
                 '128) here begins a nested list.\n',
                 '     + apples\n',
                 '     + bananas\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(xpect))

    def test_bulleted_list(self):
        input = ['* **test case**:\n',
                 '  testing a link as the first item on a continuation line\n',
                 '  [links must be indented][properly].\n',
                 '\n',
                 '[properly]: uri\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_code_blocks(self):
        input = ['    this is an indented code block\n',
                 '      on two lines \n',
                 '    with some extra whitespace here and there, to be preserved  \n',
                 '      just as it is.\n',
                 '```\n',
                 'now for a fenced code block \n',
                 '  where indentation is also preserved. as are the double spaces at the end of this line:  \n',
                 '```\n',
                 '  ~~~this is an info string: behold the fenced code block with tildes!\n',
                 '  *tildes are great*\n',
                 '  ~~~\n',
                 '1. a list item with an embedded\n',
                 '\n',
                 '       indented code block.\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_html_block(self):
        input = ['<h1>some text <img src=\'https://cdn.rawgit.com/\' align=\'right\'></h1>\n',
                 '<br>\n',
                 '\n',
                 '+ <h1>html block embedded in list <img src=\'https://cdn.rawgit.com/\' align=\'right\'></h1>\n',
                 '  <br>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_block_quote(self):
        input = ['> a block quote\n',
                 '> > and a nested block quote\n',
                 '> 1. > and finally, a list with a nested block quote\n',
                 '>    > which continues on a second line.\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_link_reference_definition(self):
        input = ['[label]: https://domain.com\n',
                 '\n',
                 'paragraph [with a link][label-2], etc, etc.\n',
                 'and [a *second* link][label] as well\n',
                 'shortcut [label] & collapsed [label][]\n',
                 '\n',
                 '[label-2]: <https://libraries.io/> \'title\'\n',
                 '[label-not-referred-to]: https://foo (title)\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

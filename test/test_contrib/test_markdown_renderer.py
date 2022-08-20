from unittest import TestCase, mock
from contrib.markdown_renderer import MarkdownRenderer

from mistletoe.block_token import Document

class TestMarkdownRenderer(TestCase):
    @staticmethod
    def roundtrip(input):
        with MarkdownRenderer() as renderer:
            rendered = renderer.render(Document(input))
            return rendered

    def test_paragraphs_and_blank_lines(self):
        input = ['Paragraph 1. Single line. Followed by two white-space-only lines.\n',
                 '\n',
                 '\n',
                 'Paragraph 2. Two\n',
                 'lines, no final line break.']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input) + "\n")

    def test_line_breaks(self):
        input = ['soft line break \n',
                 'hard line break \\\n',
                 'another hard line break  \n',
                 'that\'s all.\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_span_tokens(self):
        input = ['_**emphasized and strong**_  \\*escaped\\*  `code span` ~~strikethrough~~ <h1>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_images_and_links(self):
        input = ['[a link](#url (title))\n',
                 '[another link](<someplace> \'*emphasized\n',
                 'title*\')\n',
                 '![an \\[*image*\\]](#url "title")\n',
                 '<http://foo.bar>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_thematic_break_and_headings(self):
        input = [' **  * ** * ** * **\n',
                 '## atx *heading* ##\n',
                 '# another atx heading, without ending hashes\n',
                 '\n',
                 'setext\n',
                 'heading!\n',
                 '===============\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_numbered_list(self):
        input = ['  22)  *yeah*\n',
                 '  96)\n',
                 ' 128) here begins a nested list.\n',
                 '       + apples\n',
                 '       +  bananas\n']
        xpect = ['22) *yeah*\n',
                 '96) \n',
                 '128) here begins a nested list.\n',
                 '     + apples\n',
                 '     + bananas\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(xpect))

    def test_bulleted_list(self):
        input = ['* **Fast**:\n',
                 '  mistletoe is the fastest implementation of CommonMark in Python.\n',
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
        input = ['<h1>mistletoe<img src=\'https://cdn.rawgit.com/miyuchina/mistletoe/master/resources/logo.svg\' align=\'right\' width=\'128\' height=\'128\'></h1>\n',
                 '<br>\n',
                 '\n',
                 '+ <h1>mistletoe<img src=\'https://cdn.rawgit.com/miyuchina/mistletoe/master/resources/logo.svg\' align=\'right\' width=\'128\' height=\'128\'></h1>\n',
                 '  <br>\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_block_quote(self):
        input = ['> a block quote\n',
                 '> > a nested block quote\n',
                 '> 1. > a list with a nested block quote\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_link_reference_definition(self):
        input = ['[github]: https://github.com\n',
                 '\n',
                 'on [Libraries.io][libs-dest], but this\n',
                 'list of [Dependents][github] is tracked\n',
                 'shortcut [github] & collapsed [github][]\n',
                 '\n',
                 '[libs-dest]: <https://libraries.io/> \'title\'\n',
                 '[t]: https://foo (title)\n']
        rendered = self.roundtrip(input)
        self.assertEqual(rendered, "".join(input))

    def test_roundtrip_readme(self):
        with open('README.md', 'r', encoding='utf-8') as file:
            input = file.readlines()
        rendered = self.roundtrip(input)
        with open('roundtrip.md', 'w', encoding='utf-8') as outf:
            outf.write(rendered)
        self.assertEqual("".join(input), rendered)

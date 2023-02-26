import unittest
from mistletoe import block_token
from mistletoe.markdown_renderer import MarkdownRenderer


class TestFormatting(unittest.TestCase):
    def test_wordwrap_plain_paragraph(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with only plain text and soft line breaks
            paragraph = block_token.Paragraph(
                [
                    "A \n",
                    "short   paragraph \n",
                    "   without any \n",
                    "long words \n",
                    "or hard line breaks.\n",
                ]
            )

            # when reflowing with the max line length set medium long
            lines = renderer.render(paragraph, max_line_length=30)

            # then the content is reflowed accordingly
            assert lines == (
                "A short paragraph without any\n"
                "long words or hard line\n"
                "breaks.\n"
            )

            # when reflowing with the max line length set lower than the longest word: "paragraph", 9 chars
            lines = renderer.render(paragraph, max_line_length=8)

            # then the content is reflowed so that the max line length is only exceeded for long words
            assert lines == (
                "A short\n"
                "paragraph\n"
                "without\n"
                "any long\n"
                "words or\n"
                "hard\n"
                "line\n"
                "breaks.\n"
            )

    def test_wordwrap_paragraph_with_emphasized_words(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with emphasized words
            paragraph = block_token.Paragraph(
                [
                    "*emphasized* _nested *emphasis* too_\n"
                ]
            )

            # when reflowing with the max line length set very short
            lines = renderer.render(paragraph, max_line_length=1)

            # then the content is reflowed to make the lines as short as possible (but not shorter).
            assert lines == (
                "*emphasized*\n"
                "_nested\n"
                "*emphasis*\n"
                "too_\n"
            )

    def test_wordwrap_paragraph_with_inline_code(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with inline code
            paragraph = block_token.Paragraph(
                [
                    "`inline code` and\n"
                    "``inline with\n"
                    "line break``\n"
                ]
            )

            # when reflowing with the max line length set very short
            lines = renderer.render(paragraph, max_line_length=1)

            # then the content is reflowed to make the lines as short as possible (but not shorter),
            # and the formatting of the inline code is preserved.
            assert lines == (
                "`inline code`\n"
                "and\n"
                "``inline with\n"
                "line break``\n"
            )

    def test_wordwrap_paragraph_with_hard_line_breaks(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with hard line breaks
            paragraph = block_token.Paragraph(
                [
                    "A short paragraph  \n",
                    "  without any\\\n",
                    "very long\n",
                    "words.\n",
                ]
            )

            # when reflowing with the max line length set normal long
            lines = renderer.render(paragraph, max_line_length=80)

            # then the content is reflowed with hard line breaks preserved
            assert lines == (
                "A short paragraph  \n"
                "without any\\\n"
                "very long words.\n"
            )

    def test_wordwrap_paragraph_with_link(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with a link
            paragraph = block_token.Paragraph(
                [
                    "A paragraph\n",
                    "containing [a link](<link destination with non-breaking spaces> 'which\n",
                    "has a rather long title\n",
                    "spanning multiple lines.')\n",
                ]
            )

            # when reflowing with the max line length set very short
            lines = renderer.render(paragraph, max_line_length=1)

            # then the content is reflowed to make the lines as short as possible (but not shorter)
            assert lines == (
                "A\n"
                "paragraph\n"
                "containing\n"
                "[a\n"
                "link](<link destination with non-breaking spaces>\n"
                "'which\n"
                "has\n"
                "a\n"
                "rather\n"
                "long\n"
                "title\n"
                "spanning\n"
                "multiple\n"
                "lines.')\n"
            )

    def test_wordwrap_text_in_setext_heading(self):
        with MarkdownRenderer() as renderer:
            # given a paragraph with a setext heading
            document = block_token.Document(
                [
                    "A \n",
                    "setext   heading \n",
                    "   without any \n",
                    "long words \n",
                    "or hard line breaks.\n",
                    "=====\n"
                ]
            )

            # when reflowing with the max line length set medium long
            lines = renderer.render(document, max_line_length=30)

            # then the content is reflowed accordingly
            assert lines == (
                "A setext heading without any\n"
                "long words or hard line\n"
                "breaks.\n"
                "=====\n"
            )

    def test_wordwrap_text_in_link_reference_definition(self):
        with MarkdownRenderer() as renderer:
            # given some markdown with link reference definitions
            document = block_token.Document(
                [
                    "[This is\n",
                    "  the *link label*.]:<a long, non-breakable link reference> 'title (with parens). new\n",
                    "lines allowed.'\n",
                    "[*]:url  'Another   link      reference\tdefinition'\n",
                ]
            )

            # when reflowing with the max line length set short
            lines = renderer.render(document, max_line_length=30)

            # then the content is reflowed accordingly
            assert lines == (
                "[This is the *link label*.]:\n"
                "<a long, non-breakable link reference>\n"
                "'title (with parens). new\n"
                "lines allowed.'\n"
                "[*]:url 'Another link\n"
                "reference definition'\n"
            )

    def test_wordwrap_paragraph_in_list(self):
        with MarkdownRenderer() as renderer:
            # given some markdown with a nested list
            document = block_token.Document(
                [
                    "1. List item\n",
                    "2. A second list item including:\n",
                    "   * Nested list.\n",
                    "     This is a continuation line\n",
                ]
            )

            # when reflowing with the max line length set medium long
            lines = renderer.render(document, max_line_length=25)

            # then the content is reflowed accordingly
            assert lines == (
                "1. List item\n"
                "2. A second list item\n"
                "   including:\n"
                "   * Nested list. This is\n"
                "     a continuation line\n"
            )

    def test_wordwrap_paragraph_in_block_quote(self):
        with MarkdownRenderer() as renderer:
            # given some markdown with nested block quotes
            document = block_token.Document(
                [
                    "> Devouring Time, blunt thou the lion's paws,\n",
                    "> And make the earth devour her own sweet brood;\n",
                    "> > When Dawn strides out to wake a dewy farm\n",
                    "> > Across green fields and yellow hills of hay\n",
                ]
            )

            # when reflowing with the max line length set medium long
            lines = renderer.render(document, max_line_length=30)

            # then the content is reflowed accordingly
            assert lines == (
                "> Devouring Time, blunt thou\n"
                "> the lion's paws, And make\n"
                "> the earth devour her own\n"
                "> sweet brood;\n"
                "> > When Dawn strides out to\n"
                "> > wake a dewy farm Across\n"
                "> > green fields and yellow\n"
                "> > hills of hay\n"
            )

    def test_wordwrap_tables(self):
        with MarkdownRenderer() as renderer:
            # given a markdown table
            input = (
                [
                    "| header |                         x |                 |\n",
                    "| ------ | ------------------------: | --------------- |\n",
                    "| .      | Performance improvements. | an extra column |\n",
                ]
            )
            document = block_token.Document(input)

            # when reflowing
            lines = renderer.render(document, max_line_length=30)

            # then the table is rendered without any word wrapping
            assert lines == "".join(input)

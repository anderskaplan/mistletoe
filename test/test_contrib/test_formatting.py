import unittest
from mistletoe import block_token
from mistletoe.markdown_renderer import MarkdownRenderer


class TestFormatting(unittest.TestCase):
    def test_wordwrap_plain_paragraph(self):
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
        with MarkdownRenderer() as renderer:
            lines = renderer.render(paragraph, max_line_length=30)

        # then the content is reflowed accordingly
        assert lines == (
            "A short paragraph without any\n"
            "long words or hard line\n"
            "breaks.\n"
        )

        # when reflowing with the max line length set lower than the longest word: "paragraph", 9 chars
        with MarkdownRenderer() as renderer:
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
        # given a paragraph with emphasized words
        paragraph = block_token.Paragraph(
            [
                "*emphasized* _nested *emphasis* too_\n"
            ]
        )

        # when reflowing with the max line length set very short
        with MarkdownRenderer() as renderer:
            lines = renderer.render(paragraph, max_line_length=1)

        # then the content is reflowed to make the lines as short as possible (but not shorter).
        assert lines == (
            "*emphasized*\n"
            "_nested\n"
            "*emphasis*\n"
            "too_\n"
        )

    def test_wordwrap_paragraph_with_inline_code(self):
        # given a paragraph with inline code
        paragraph = block_token.Paragraph(
            [
                "`inline code` and\n"
                "``inline with\n"
                "line break``\n"
            ]
        )

        # when reflowing with the max line length set very short
        with MarkdownRenderer() as renderer:
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
        with MarkdownRenderer() as renderer:
            lines = renderer.render(paragraph, max_line_length=80)

        # then the content is reflowed with hard line breaks preserved
        assert lines == (
            "A short paragraph  \n"
            "without any\\\n"
            "very long words.\n"
        )

    def test_wordwrap_paragraph_with_link(self):
        # given a paragraph with a link
        paragraph = block_token.Paragraph(
            [
                "A paragraph\n",
                "containing [a link](<url%20> 'which\n",
                "has a rather long title\n",
                "spanning multiple lines.')\n",
            ]
        )

        # when reflowing with the max line length set very short
        with MarkdownRenderer() as renderer:
            lines = renderer.render(paragraph, max_line_length=1)

        # then the content is reflowed to make the lines as short as possible (but not shorter)
        assert lines == (
            "A\n"
            "paragraph\n"
            "containing\n"
            "[a\n"
            "link](<url%20>\n"
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
        with MarkdownRenderer() as renderer:
            lines = renderer.render(document, max_line_length=30)

        # then the content is reflowed accordingly
        assert lines == (
            "A setext heading without any\n"
            "long words or hard line\n"
            "breaks.\n"
            "=====\n"
        )

    def test_wordwrap_paragraph_in_list(self):
        assert False

    def test_wordwrap_paragraph_in_nested_containers(self):
        # list, block quote
        assert False

    def test_wordwrap_ignore_tables(self):
        assert False

    def test_wordwrap_link_reference_definition(self):
        # link ref with long label and long title
        assert False

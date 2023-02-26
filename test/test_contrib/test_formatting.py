import unittest
from mistletoe.contrib.formatting import wordwrap
from mistletoe import block_token


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

        # when reflowing with the max line length set medium high
        lines = wordwrap(paragraph, max_line_length=30)

        # then the content is reflowed accordingly
        assert lines == (
            "A short paragraph without any\n"
            "long words or hard line\n"
            "breaks."
        )

        # when reflowing with the max line length set lower than the longest word: "paragraph", 9 chars
        lines = wordwrap(paragraph, max_line_length=8)

        # then the content is reflowed so that the max line length is only exceeded for long words
        assert lines == (
            "A short\n"
            "paragraph\n"
            "without\n"
            "any long\n"
            "words or\n"
            "hard\n"
            "line\n"
            "breaks."
        )

    def test_wordwrap_paragraph_with_emphasized_words(self):
        # given a paragraph with emphasized words
        paragraph = block_token.Paragraph(
            [
                "*emphasized* _nested *emphasis* too_\n"
            ]
        )

        # when reflowing with the max line length set very short
        lines = wordwrap(paragraph, max_line_length=1)

        # then the content is reflowed to make the lines as short as possible (but not shorter).
        assert lines == (
            "*emphasized*\n"
            "_nested\n"
            "*emphasis*\n"
            "too_"
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
        lines = wordwrap(paragraph, max_line_length=1)

        # then the content is reflowed to make the lines as short as possible (but not shorter),
        # and the formatting of the inline code is preserved.
        assert lines == (
            "`inline code`\n"
            "and\n"
            "``inline with\n"
            "line break``"
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

        # when reflowing with the max line length set medium high
        lines = wordwrap(paragraph, max_line_length=80)

        # then the content is reflowed with hard line breaks preserved
        assert lines == (
            "A short paragraph  \n"
            "without any\\\n"
            "very long words."
        )

    def test_wordwrap_paragraph_with_link(self):
        # wide & narrow. title with newline
        assert False

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

        # when reflowing with the max line length set medium high
        lines = wordwrap(document, max_line_length=30)

        # then the content is reflowed accordingly
        assert lines == (
            "A setext heading without any\n"
            "long words or hard line\n"
            "breaks.\n"
            "====="
        )

    def test_wordwrap_paragraph_in_list(self):
        assert False

    def test_wordwrap_paragraph_in_nested_containers(self):
        # list, block quote
        assert False

    def test_wordwrap_ignore_tables(self):
        assert False

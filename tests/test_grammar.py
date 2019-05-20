from grammar import Grammar
import unittest


class GrammarTests(unittest.TestCase):
    def test_basic(self):
        x = Grammar([
            "S -> C C",
            "C -> e C | d",
        ])
        self.assertEqual(x.first_sets(), {"S": {"e", "d"}, "C": {"e", "d"}})

    def test_multirule(self):
        w = Grammar([
            "S -> a b c",
            "S -> a b",
            "S -> a"
        ])
        x = Grammar([
            "S -> a b c | a b",
            "S -> a"
        ])
        y = Grammar([
            "S -> a b c | a b | a"
        ])
        self.assertEqual(w, x)
        self.assertEqual(x, y)

    def test_epsilon(self):
        x = Grammar([
            "S -> A B C",
            "A -> a | #",
            "B -> A D | b",
            "C -> c d",
            "D -> d | #"
        ])
        self.assertEqual(x.first_sets(), {
            "S": {"a", "d", "b", "c"},
            "A": {"a", "#"},
            "B": {"a", "d", "b", "#"},
            "C": {"c"},
            "D": {"d", "#"},
        })

    def test_lexer_prefix1(self):
        x = Grammar([
            "S -> abc | abcd"
        ])
        self.assertEqual(
            x.lex("abcd abc"),
            [("abcd", "abcd"), ("abc", "abc")],
        )

    def test_lexer_prefix2(self):
        x = Grammar([
            "S -> abc | ID"
        ])
        self.assertEqual(
            x.lex("abcd abc", {"ID": ".+"}),
            [("abcd", "abcd"), ("abc", "abc")],
        )

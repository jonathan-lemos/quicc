from grammar import CFGException, Grammar
import unittest


class EqTests(unittest.TestCase):
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


class FirstFollowTests(unittest.TestCase):
    def test_basic(self):
        x = Grammar([
            "S -> C C",
            "C -> e C | d",
        ])
        self.assertEqual(x.first_sets(), {"S": {"e", "d"}, "C": {"e", "d"}})

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


class LexTests(unittest.TestCase):
    def test_lexer_prefix1(self):
        x = Grammar([
            "S -> abc | abcd"
        ])
        self.assertEqual(
            x.lex(["abcd abc"]),
            [("abcd", "abcd"), ("abc", "abc")],
        )

    def test_lexer_prefix2(self):
        x = Grammar([
            "S -> abc | ID"
        ])
        self.assertEqual(
            x.lex(["abcd abc"], {"ID": "[a-z]+"}),
            [("ID", "abcd"), ("abc", "abc")],
        )

    def test_terminal(self):
        x = Grammar([
            "S -> A B",
            "A -> c | d",
            "B -> ef | g S",
        ])

        self.assertRaises(CFGException, lambda: x.lex(["d A"]))

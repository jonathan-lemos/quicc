from grammar import Grammar
import unittest


class FirstFollowSets(unittest.TestCase):
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
            "C -> c",
            "D -> d | #"
        ])
        self.assertEqual(x.first_sets(), {
            "S": {"a", "d", "b", "c"},
            "A": {"a", "#"},
            "B": {"a", "d", "b", "#"},
            "C": {"c"},
            "D": {"d", "#"},
        })


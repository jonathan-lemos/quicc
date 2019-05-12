from grammar import Grammar
import unittest


class FirstFollowSets(unittest.TestCase):
    def test_basic(self):
        x = Grammar([
            "S -> C C",
            "C -> e C | d",
        ])
        self.assertEqual(x.first_sets(), {"S": {"e", "d"}, "C": {"e", "d"}})


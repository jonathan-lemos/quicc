from grammar import Grammar
from parser import LR1Parser, ParseException
import unittest

class ParserTest(unittest.TestCase):
    def test_basic(self):
        x = Grammar([
            "S -> C C",
            "C -> e C | d",
        ])
        y = LR1Parser(x)

        y.parse("edeeed")
        y.parse("dd")
        self.assertRaises(ParseException, lambda: y.parse("d"))
        self.assertRaises(ParseException, lambda: y.parse("edede"))

    def test_epsilon(self):
        x = Grammar([
            "E -> E + T | E",
            "T -> T x F | F"
        ])
        y = LR1Parser(x)


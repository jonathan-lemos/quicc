from collections import deque
from functools import reduce
from copy import deepcopy
import itertools
import re
from typing import Callable, Deque, Dict, Iterable, List, Pattern, Sequence, Set, Tuple, TypeVar, Union


class Grammar:
    __rules: Dict[str, Set[Tuple[str]]] = {}
    __start: str = ""

    __T = TypeVar("__T")

    """
    Computes the "epsilon power set" of all possibilities of a token being in a production.
    This is used for removing epsilons, hence the name.
    
    Example: AbcAdeA for A would become {'bcde', 'Abcde', 'bcAde', 'bcdeA', 'AbcAde', 'AbcdeA', 'bcAdeA', 'AbcAdeA'}
    :param l: The production to iterate
    :param s: The token to iterate over
    :returns: The "epsilon power set"
    """
    @staticmethod
    def __epsilon_iter(l: Tuple[str], s: str) -> List[Tuple[str]]:
        # power set bit strings. length = occurences in S
        # 0 represents "not in the set", 1 represents "in the set"
        bitstrings = ["".join(seq) for seq in itertools.product("01", repeat=l.count(s))]
        output = []
        for bs in bitstrings:
            tmp = []
            ctr = 0
            # for each token in the production
            for c in l:
                # if the token is not our iterator, append it to tmp
                if c != s:
                    tmp.append(c)
                # otherwise only append it if the bitstring at this char is a 0
                else:
                    if bs[ctr] == "1":
                        tmp.append(c)
                    ctr += 1
            # if there's nothing in our tmp, append epsilon
            if len(tmp) == 0:
                output.append(("#",))
            # otherwise append tmp
            else:
                output.append(tuple(tmp))
        return output

    """
    Returns the indices where a particular element appears in a sequence
    
    Example: AbcAdeA would become (0, 3, 6)
    :param l: The sequence
    :param s: The token to get the indices of
    :returns: The indices
    """
    @staticmethod
    def __indices(l: Sequence[__T], s: __T) -> Tuple[int]:
        indices = []
        for i in range(len(l)):
            if l[i] == s:
                indices.append(i)
        return tuple(indices)

    """
    Returns the first index that matches a given lambda
    
    :param fn: The lambda to check. Returns true if iteration should stop.
    :param c: A sequence to iterate over
    :returns: The index, or -1 if not found
    """
    @staticmethod
    def __first(fn: Callable[[__T], bool], c: Sequence[__T]) -> int:
        for i in range(len(c)):
            if fn(c[i]):
                return i
        return -1

    """
    Lexes a production's right hand side into a sequence of tokens.
    For example, 'A B cde "fgh ijk" r"[0-9]+"' turns into ['A', 'B', 'cde', '"fgh ijk"', 'r"[0-9]+"']
    
    Spaces in quotations are preserved.
    r"string" denotes a regex.
    
    :param rhs: The string to lex
    :returns: The sequence of tokens
    """
    @staticmethod
    def __lex_rhs(rhs: str) -> Sequence[str]:
        ret: List[str] = []
        cur: str = ""
        quote = False
        escape = False
        last_ws = True
        for c in rhs + " ":
            if escape:
                cur += c
                escape = False
                last_ws = False
                continue
            if c == " ":
                if not quote:
                    if cur.strip() != "":
                        ret.append(cur)
                    cur = ""
                else:
                    cur += c
                last_ws = True
                continue
            if c == "\"":
                if not quote and not last_ws:
                    raise Exception("Quotes can only appear as complete tokens")
                quote = not quote
                last_ws = False
                continue
            if c == "\\" and not quote:
                escape = True
                last_ws = False
                continue
            cur += c
            last_ws = False
        if quote:
            raise Exception("Missing closing quote")
        if escape:
            raise Exception("Escape at end of string")
        return ret

    """
    Constructs a grammar out of a set of rules
    Rules are given as a list of strings.
    Each string looks like the following:
    
    nonterm -> term nonterm term ab c | # | "ab c" r"[0-9]+"
    
    Tokens are separated by spaces.
    A regex can be given with r"your_regex_here"
    Any token in quotes preserves spaces
    A quote can be escaped with \"
    
    The starting symbol is the first in the grammar.
    
    :param cfg: A list of rules as described above
    :raise Exception: Error parsing cfg
    """
    def __init__(self, cfg: Iterable[str] = ()):
        self.__start = ""

        for rule in cfg:
            # split name of rule and its right hand side
            a = [x.strip() for x in rule.split("->")]
            if len(a) < 2:
                raise Exception("\"->\" not found in rule \"" + rule + "\"")
            if len(a) > 2:
                raise Exception("Multiple \"->\" found in rule \"" + rule + "\"")

            if self.__start == "":
                self.__start = a[0]

            # split by "|"
            b = [x.strip() for x in a[1].split("|")]
            if len(b) == 0:
                raise Exception("Cannot have empty right hand in CFG")

            if not a[0] in self.__rules:
                self.__rules[a[0]] = set()

            # foreach rule in b,
            for r in b:
                # get rid of epsilons unless epsilon is the only member of that rule
                lex = self.__lex_rhs(r)
                c = tuple(x for x in lex if len(lex) == 1 or x != "#")
                if len(c) == 0:
                    raise Exception("Cannot have empty rules in CFG rule \"" + r + "\"")
                # add it to the list
                self.__rules[a[0]].add(c)

    """
    Returns all the productions in the given grammar.
    
    :returns: An iterable containing (nonterm, production)
    """
    def __prods(self) -> Iterable[Tuple[str, Tuple[str]]]:
        return ((nt, prod) for nt in self for prod in self[nt])

    """
    Returns all the productions that can appear at the beginning of a rule.
    """
    def __first_iter_rec(self, r: Tuple[str, Tuple[str]], nt_found: Set[str]) -> Iterable[Tuple[str, Tuple[str]]]:
        if r[1][0] in nt_found:
            return
        yield r
        if r[1][0] not in self:
            return
        else:
            for prod in list(self[r[1][0]]):
                yield from self.__first_iter_rec((r[1][0], prod), nt_found | {r[0]})

    """
    Computes the first set of a given production
    
    :param r: (nonterminal, production to match)
    :returns: A set of terminals that can appear first in a given production
    """
    def __first_set(self, r: Tuple[str, Tuple[str]]) -> Set[str]:
        ret: Set[str] = set()
        for prod in self.__first_iter_rec(r, set()):
            if prod[1][0] not in self:
                ret.add(prod[1][0])
        return ret

    def __left_factor(self):
        for nt in self:
            cur: Dict[str, int] = {}
            for prod in self[nt]:
                if prod[0] not in self:
                    if prod[0] in cur:
                        cur[prod[0]] += 1
                    else:
                        cur[prod[0]] = 1
            newr = {x: y for (x, y) in cur.items() if y >= 2}

    def __parse_rdp(self, tokens: Sequence[Tuple[str, str]], prod: Tuple[str], ind: int) -> Union[List[Union[Tuple[str, str], List]], None]:
        output: List[Union[Tuple[str, str], List]] = []

        for t in prod:
            n = tokens[ind]
            ind = ind + 1
            if n[1] in self:
                a: Union[Tuple[str, str], List]
                for prod in self[n[1]]:
                    a = self.__parse_rdp(tokens, prod, ind)
                    if a is not None:
                        ind += len(a)
                        break
                if a is None:
                    return None
                output.append(a)

        return output

    """
    Removes epsilon productions from the grammar.
    """
    def remove_epsilon(self):
        # if the start rule appears in any production
        if len(list(filter(lambda s: self.__start in s, [x[1] for x in self.__prods()]))) > 0:
            # add a new start state that produces the current one
            szero = self.__start + "0"
            self[szero] = {(self.__start,)}
            self.__rules[szero] = {(self.__start,)}
            self.__start = szero

        rules_iter = list(self.__rules)
        for _ in rules_iter:
            for nt1 in rules_iter:
                nt1: str = nt1
                if len([x for x in self.__rules[nt1] if x == ('#',)]) == 0:
                    continue
                for nt2 in rules_iter:
                    nt2: str = nt2
                    eps = filter(lambda x: x[1] > 0, [(x, x.count(nt1)) for x in self.__rules[nt2]])
                    for rule in eps:
                        new = self.__epsilon_iter(rule[0], nt1)
                        for x in new:
                            self.__rules[nt2].add(x)
        for nt in rules_iter:
            if nt == self.__start:
                continue
            if ("#",) in self.__rules[nt]:
                self.__rules[nt].remove(("#",))

    """
    Removes any kind of left recursion from the grammar.
    """
    def remove_recursion(self):
        rules_iter: Sequence[str] = list(self.__rules)
        for nt1 in rules_iter:
            nt1: str = nt1
            for nt2 in rules_iter:
                nt2: str = nt2
                if nt1 == nt2:
                    continue
                cur_rules = deepcopy(self.__rules[nt1])
                for rule in cur_rules:
                    rule: Tuple[str] = rule
                    index = self.__first(lambda x: x != nt2, rule)
                    if index == -1:
                        index = len(rule)
                    if index > 0:
                        self.__rules[nt1].remove(rule)
                        for r in self.__rules[nt2]:
                            self.__rules[nt1].add(tuple((list(r) * index) + list(rule[index:])))
            self.__remove_dlr(nt1)
        for nt in rules_iter:
            rules = deepcopy(self.__rules[nt])
            for rule in rules:
                if '#' in rule and len(rule) > 1:
                    self.__rules[nt].remove(rule)
                    newt = tuple([x for x in rule if x != "#"])
                    self.__rules[nt].add(newt)

    """
    Removes rules that cannot be reached from the grammar.
    """
    def remove_unused(self):
        found = set()
        rem = {self.__start}
        while len(rem) > 0:
            n = rem.pop()
            if n in found:
                continue
            found.add(n)
            if n not in self.__rules:
                continue
            for rule in self.__rules[n]:
                for c in rule:
                    rem.add(c)
        for nt in list(self.__rules):
            if nt not in found:
                self.__rules.pop(nt)

    def fix(self):
        self.remove_recursion()
        self.remove_unused()
        self.remove_epsilon()
        self.remove_unused()

    """
    Returns the start symbol of the given grammar.
    """
    def start(self) -> str:
        return self.__start

    def first_sets(self) -> Dict[str, Set[str]]:
        return {x: reduce(lambda a, c: a | self.__first_set((x, c)), self[x], set()) for x in self}

    def follow_sets(self) -> Dict[str, Set[str]]:
        ret: Dict[str, Set[str]] = {}
        for nt in self:
            if nt == self.__start:
                ret[nt] = {"$"}
            else:
                ret[nt] = set()

        fs: Dict[str, Set[str]] = self.first_sets()

        while True:
            tmp = deepcopy(ret)
            for nt1 in self:
                tm = set() if nt1 != self.__start else {"$"}
                for nt2 in self:
                    for prod in self[nt2]:
                        if prod == ("#",):
                            continue
                        ind = self.__indices(prod, nt1)
                        for i in ind:
                            st: Set[str] = set()
                            while i < len(prod) - 1:
                                char = prod[i + 1]
                                if char not in tmp:
                                    st |= {char}
                                    break

                                s = fs[char]
                                if "#" not in s:
                                    st |= s
                                    break

                                st |= (fs[char] - {'#'})
                                i = i + 1

                            if i >= len(prod) - 1:
                                st |= tmp[nt2]

                            tm |= st
                ret[nt1] = tm
            if tmp == ret:
                break

        return ret

    def lex(self, ip: Iterable[str], spcl: Dict[str, Pattern[str]] = None) -> Sequence[Tuple[str, str]]:
        if spcl is None:
            spcl = {}

        tokens: Set[str] = {tok for nt in self for prod in self[nt] for tok in prod if tok not in self}

        ret: List[Tuple[str, str]] = []
        for line in ip:
            line = line.strip()
            while line != "":
                longest: Tuple[str, str] = ("", "")
                for s in tokens:
                    if line.startswith(s):
                        longest = (s, s) if len(s) > len(longest[0]) else longest
                for name in spcl:
                    r = spcl[name].match(line, 0)
                    if r is not None:
                        longest = (r[0], name) if len(r[0]) > len(longest[0]) else longest
                if longest[0] == "":
                    longest = (line[0], "ERROR")
                ret.append(longest)
                line = line[len(longest[0]):].strip()
        return ret

    # warning - extremely slow
    def parse_rdp(self, tokens: Sequence[Tuple[str, str]]):
        pass

    def parse_ll1(self, tokens: Sequence[Tuple[str, str]]) -> Dict[str, Dict[str, Union[str, Tuple[str]]]]:
        token_types: List[str] = list({typ for (_, typ) in tokens})
        first_sets: Dict[str, Set[str]] = self.first_sets()
        follow_sets: Dict[str, Set[str]] = self.follow_sets()
        ll1_table: Dict[str, Dict[str, Union[str, Tuple[str]]]] = {}
        for nt in self:
            ll1_table[nt] = {}
            for prod in self[nt]:
                if prod == ("#",):
                    f = follow_sets[nt]
                    for sym in f:
                        if sym in ll1_table[nt]:
                            raise Exception("LL(1) table conflict " + nt + "(" + str(prod) + "," + ll1_table[nt][sym] + ")")
                        ll1_table[nt][sym] = prod
                elif prod[0] not in self:
                    ll1_table[nt][prod[0]] = prod
                else:
                    ll1_table[nt][prod[0]] = prod[0]
        return ll1_table

    def __remove_dlr(self, rule: str):
        new_rule = set()

        def f(y): return y != rule

        lrec: List[Tuple[List[str], List[str]]] = [(x[:self.__first(f, x)], x[self.__first(f, x):]) for x in self.__rules[rule] if self.__first(f, x) != -1 and self.__first(f, x) > 0]
        notlrec: List[Tuple[str]] = [x for x in self.__rules[rule] if self.__first(f, x) == 0]
        ruleprime = rule + "'"

        if len(lrec) == 0:
            return

        for n in notlrec:
            new_rule.add(tuple(list(n) + [ruleprime]))

        new_rule_prime = {("#",)}

        for a, b in lrec:
            new_rule_prime.add(tuple(list(a)[1:] + list(b) + [ruleprime]))

        self.__rules[rule] = new_rule
        self.__rules[ruleprime] = new_rule_prime

    def __contains__(self, rule: str):
        return rule in self.__rules

    def __getitem__(self, rule: str) -> Set[Tuple[str]]:
        return self.__rules[rule]

    def __iter__(self):
        x = self.__start
        y = [x for x in self.__rules if x != self.__start]
        return iter([x] + y)

    def __len__(self):
        return len(self.__rules)

    def __setitem__(self, key: str, rule: Set[Tuple[str]]):
        self.__rules[key] = rule

    def __str__(self):
        return reduce(lambda a, v: a + "\n" + v[0] + " -> " + reduce(lambda d, e: d + " | " + reduce(lambda b, c: b + " " + (c if c != "#" else "Ɛ"), e, "")[1:], v[1], "")[3:], [(x, self.__rules[x]) for x in self], "")[1:]


def main():
    x = Grammar([
        "program -> declaration-list",
        "declaration-list -> declaration-list declaration | declaration",
        "declaration -> var-declaration | fun-declaration",
        "var-declaration -> type-specifier ID ; | type-specifier ID [ NUM ] ;",
        "type-specifier -> int | void | float",
        "fun-declaration -> type-specifier ID ( params ) compound-stmt",
        "params -> param-list | void",
        "param-list -> param-list , param | param",
        "param -> type-specifier ID | type-specifier ID [ ]",
        "compound-stmt -> { local-declarations statement-list }",
        "local-declarations -> local-declarations var-declaration | #",
        "statement-list -> statement-list statement | #",
        "statement -> expression-stmt | compound-stmt | selection-stmt | iteration-stmt | return-stmt",
        "expression-stmt -> expression ; | ;",
        "selection-stmt -> if ( expression ) statement | if ( expression ) statement else statement",
        "iteration-stmt -> while ( expression ) statement",
        "return-stmt -> return ; | return expression ;",
        "expression -> var = expression | simple-expression",
        "var -> ID | ID [ expression ]",
        "simple-expression -> additive-expression relop additive-expression | additive-expression",
        "relop -> <= | < | > | >= | == | !=",
        "additive-expression -> additive-expression addop term | term",
        "addop -> + | -",
        "term -> term mulop factor | factor",
        "mulop -> * | /",
        "factor -> ( expression ) | var | call | NUM",
        "call -> ID ( args )",
        "args -> arg-list | #",
        "arg-list -> arg-list , expression | expression",
    ])
    print(x.lex([
        "int main(void) {",
        "   return 0;",
        "}"
    ], {
        "ID": re.compile("[A-Za-z]+"),
        "NUM": re.compile("\\d+|\\d\\.\\d+")
    }))
    print()
    print(str(x))
    print()
    fs = x.first_sets()
    for v in fs:
        print(v + " -> " + str(fs[v]))


if __name__ == '__main__':
    main()

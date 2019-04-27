from functools import reduce
import itertools
from typing import Callable, Dict, Iterable, Iterator, List, Pattern, Sequence, Set, Tuple, TypeVar


class CFGException(Exception):
    pass


__T = TypeVar("__T")

"""
Returns the indices where a particular element appears in a sequence
    
Example: AbcAdeA would become (0, 3, 6)
:param l: The sequence
:param s: The token to get the indices of
:returns: The indices
"""
def indices(l: Sequence[__T], s: __T) -> Tuple[int]:
    ind = []
    for i in range(len(l)):
        if l[i] == s:
            ind.append(i)
    return tuple(ind)

"""
Returns the first index that matches a given lambda
    
:param fn: The lambda to check. Returns true if iteration should stop.
:param c: A sequence to iterate over
:returns: The index, or -1 if not found
"""
def first(fn: Callable[[__T], bool], c: Sequence[__T]) -> int:
    for i in range(len(c)):
        if fn(c[i]):
            return i
    return -1

"""
Computes the "epsilon power set" of all possibilities of a token being in a production.
This is used for removing epsilons, hence the name.

Example: AbcAdeA for A would become {'bcde', 'Abcde', 'bcAde', 'bcdeA', 'AbcAde', 'AbcdeA', 'bcAdeA', 'AbcAdeA'}
:param l: The production to iterate
:param s: The token to iterate over
:returns: The "epsilon power set"
"""
def epsilon_iter(l: Tuple[str], s: str) -> List[Tuple[str]]:
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
Lexes a production's right hand side into a sequence of tokens.
For example, 'A B cde "fgh \\"\\\\ ijk"' turns into ['A', 'B', 'cde', 'fgh "\ ijk']

Spaces in quotations are preserved.
r"string" denotes a regex.

:param rhs: The string to lex
:returns: The sequence of tokens
"""
def tokenize(rhs: str) -> Tuple[str]:
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
    if len(ret) != 1:
        return tuple(filter(lambda x: x != "#", ret))
    else:
        return tuple(ret)


class Nonterm:
    __symbol: str = ""
    __productions: Set[Tuple[str]]

    def __init__(self, nt: str, *rhs: str):
        if len(rhs) == 0:
            raise CFGException("A Nonterm needs to be produced out of at least one string")

        self.__symbol = nt

        for st in rhs:
            self.__productions = {tokenize(x) for x in st.split("|")}

    def symbol(self):
        return self.__symbol

    def __iter__(self) -> Iterator[Tuple[str]]:
        return iter(self.__productions)

    def __str__(self) -> str:
        def p2s(prod: Tuple[str]) -> str:
            return reduce(lambda a, b: a + " " + b, prod)

        return self.__symbol + " -> " + reduce(lambda a, b: a + " | " + p2s(b), self.__productions, "")[3:]


class Grammar:
    __rules: Dict[str, Nonterm] = {}
    __terminals: Set[str] = set()
    __start: str = ""

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

        vals: Dict[str, List[str]] = {}

        for rule in cfg:
            # split name of rule and its right hand side
            a = [x.strip() for x in rule.split("->")]
            if len(a) < 2:
                raise Exception("\"->\" not found in rule \"" + rule + "\"")
            if len(a) > 2:
                raise Exception("Multiple \"->\" found in rule \"" + rule + "\"")

            sym, rhs = a

            if self.__start == "":
                self.__start = sym

            if sym not in vals:
                vals[sym] = [rhs]
            else:
                vals[sym].append(rhs)

        self.__rules = {nt: Nonterm(nt, *vals[nt]) for nt in vals}

        self.__terminals = {x for _, prod in self for x in prod if x not in self.nonterms()}

    """
    Returns the start symbol of the grammar
    """
    def start(self) -> str:
        return self.__start

    """
    Returns all of the non-terminals in the grammar.
    The first nonterm is always the start symbol.
    
    :returns: All of the non-terminals in the grammar.
    """
    def nonterms(self) -> Sequence[str]:
        return [self.start()] + list(set(self.__rules) - {self.start()})

    """
    Returns all of the terminals in the grammar.
    """
    def terminals(self) -> Iterable[str]:
        return self.__terminals

    def epsilon_nonterms(self) -> Set[str]:
        ret = {"#"}

        while True:
            len_tmp = len(ret)
            for nt, prod in self:
                hit = False
                for token in prod:
                    if token not in prod:
                        hit = True
                        break
                if not hit:
                    ret |= {nt}
            if len_tmp == len(ret):
                return ret

    def first_sets(self) -> Dict[str, Set[str]]:
        ret = {}
        for nt in self.nonterms():
            ret[nt] = set()
        for t in self.terminals():
            ret[t] = {t}
        epsilons = self.epsilon_nonterms()

        while True:
            updated = False
            for nt, prod in self:
                for token in prod:
                    tmp = len(ret[nt])
                    ret[nt] |= ret[token]
                    updated |= len(ret[nt]) != tmp
                    if token not in epsilons:
                        break
            if not updated:
                return ret

    def follow_sets(self) -> Dict[str, Set[str]]:
        fs = self.first_sets()
        epsilons = self.epsilon_nonterms()
        ret = {}
        for nt in self.nonterms():
            ret[nt] = set()

        while True:
            updated = False

            def update(s1: Set[str], s2: Set[str]) -> None:
                global updated
                tmp = len(s1)
                s1 |= s2
                updated = len(s1) == tmp

            for nt, prod in self:
                for token in reversed(prod):
                    if token in ret:
                        update(ret[token], ret[nt])
                        if token in epsilons:
                            update(ret[nt], ret[token])
                        else:
                            update(ret[nt], fs[token])
            if not updated:
                return ret

    def lex(self, ip: Iterable[str], spcl: Dict[str, Pattern[str]] = None) -> Sequence[Tuple[str, str]]:
        if spcl is None:
            spcl = {}

        ret: List[Tuple[str, str]] = []
        for line in ip:
            line = line.strip()
            while line != "":
                longest: Tuple[str, str] = ("", "")
                for s in self.terminals():
                    if line.startswith(s):
                        longest = (s, s) if len(s) > len(longest[0]) else longest
                for name in spcl:
                    r = spcl[name].match(line, 0)
                    if r is not None:
                        longest = (r[0], name) if len(r[0]) > len(longest[0]) else longest
                if longest[0] == "":
                    raise CFGException("Invalid token starting with \"" + line + "\"")
                ret.append(longest)
                line = line[len(longest[0]):].strip()
        return ret

    def __contains__(self, nt: str) -> bool:
        return nt in self.__rules

    def __getitem__(self, nt: str) -> Nonterm:
        return self.__rules[nt]

    def __iter__(self) -> Iterator[Tuple[str, Tuple[str]]]:
        for nt in self.nonterms():
            for prod in self[nt]:
                yield (nt, prod)

    def __len__(self) -> int:
        return len(self.__rules)

    def __str__(self) -> str:
        return reduce(lambda a, v: a + "\n" + str(v), [self[nt] for nt in self.nonterms()], "")[1:]


def main():
    x = Grammar([
        "S -> H",
        "H -> A B C",
        "A -> C m | a g | #",
        "B -> B a | #",
        "C -> C p | p | A",
    ])
    print(str(x))
    s1 = x.first_sets()
    print("First sets")
    print("----------")
    for y in s1:
        print(y + ": " + str(s1[y]))
    fs = x.follow_sets()
    print("Follow sets")
    print("----------")
    for y in fs:
        print(y + ": " + str(fs[y]))
    """
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
    """


if __name__ == '__main__':
    main()

from functools import reduce
import re
from typing import Dict, FrozenSet, Iterable, Iterator, List, Sequence, Set, Tuple, Union


class CFGException(Exception):
    pass


def tokenize(rhs: str) -> Tuple[str]:
    """
    Lexes a production's right hand side into a sequence of tokens.
    For example, 'A B cde "fgh \\"\\\\ ijk"' turns into ['A', 'B', 'cde', 'fgh "\\ ijk']

    Spaces in quotations are preserved.
    r"string" denotes a regex.

    :param rhs: The string to lex
    :returns: The sequence of tokens
    """

    ret: List[str] = []
    cur: str = ""
    quote = False
    escape = False
    last_ws = True
    # extra " " ends quotes properly
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
    __productions: FrozenSet[Tuple[str]]
    __hash: int

    def __init__(self, nt: str, *rhs: Union[str, Tuple[str]]):
        """
        Initializes a Nonterm
        :param nt: The symbol that these productions map to
        :param rhs: Varargs containing strings ("a b c") or tuples ("a", "b", "c")
        """

        if len(rhs) == 0:
            raise CFGException("A Nonterm needs to be produced out of at least one string")

        self.__symbol = nt

        if isinstance(rhs[0], str):
            self.__productions = frozenset(tokenize(x) for st in rhs for x in st.split("|"))
        else:
            self.__productions = frozenset(rhs)

        self.__hash = hash((self.__symbol, self.__productions))

    def symbol(self) -> str:
        """
        Returns the symbol associated with a Nonterm
        """
        return self.__symbol

    def __eq__(self, other):
        if not isinstance(other, Nonterm):
            return False
        return self.__symbol == other.__symbol and self.__productions == other.__productions

    def __hash__(self):
        return self.__hash

    def __iter__(self) -> Iterator[Tuple[str]]:
        """
        Iterates through the productions in this Nonterm. The order is not guaranteed in any way.
        """
        return iter(self.__productions)

    def __str__(self) -> str:
        return self.__symbol + " -> " + reduce(lambda a, b: a + " | " + " ".join(b), self.__productions, "")[3:]


class Grammar:
    __rules: Dict[str, Nonterm] = {}
    __terminals: Set[str] = set()
    __ent: Set[str]
    __start: str = ""
    __hash: int

    def __init_iter_str(self, cfg: Iterable[str]) -> None:
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

    def __init_tuple(self, cfg: Iterable[Tuple[str, Sequence[str]]]) -> None:
        """
        Constructs a Grammar out of a list of (nonterm, ["a", "b", "c"])
        This is used to construct a Grammar using the rules of another grammar
        :param cfg: An iterable of tuples containing (nonterm, rule)
        :return: void
        """
        vals: Dict[str, List[Sequence[str]]] = {}

        for nt, prod in cfg:
            if self.__start == "":
                self.__start = nt
            if nt not in vals:
                vals[nt] = [prod]
            else:
                vals[nt].append(prod)

        self.__rules = {nt: Nonterm(nt, *vals[nt]) for nt in vals}

        self.__terminals = {x for _, prod in self for x in prod if x not in self.nonterms()}

    def __init__(self, cfg: Union[Iterable[str], Iterable[Tuple[str, Sequence[str]]]]):
        tmp: Union[List[str], List[Tuple[str, Sequence[str]]]] = list(cfg)
        if isinstance(tmp[0], str):
            tmp: List[str] = tmp
            self.__init_iter_str(tmp)
        else:
            tmp: List[Tuple[str, Sequence[str]]] = tmp
            self.__init_tuple(tmp)

        self.__hash = hash((self.__rules.values(), self.__start))

        # calculate epsilon nonterms
        ret = {"#"}
        # while the set is changing
        while True:
            len_tmp = len(ret)
            for nt, prod in self:
                hit = False
                for token in prod:
                    # if the token is not in our current set of epsilons, stop
                    if token not in ret:
                        hit = True
                        break
                # if all the tokens could produce epsilon, add it to our set
                if not hit:
                    ret |= {nt}
            # if the set didn't change on this iteration, break
            if len_tmp == len(ret):
                self.__ent = ret

    def start(self) -> str:
        """
        Returns the start symbol of the grammar
        """
        return self.__start

    def nonterms(self) -> Sequence[str]:
        """
        Returns all of the non-terminals in the grammar.
        The first nonterm is always the start symbol.

        :returns: All of the non-terminals in the grammar.
        """
        return [self.start()] + list(set(self.__rules) - {self.start()})

    def terminals(self) -> Iterable[str]:
        """
        Returns all of the terminals in the grammar.
        """
        return self.__terminals

    def epsilon_nonterms(self) -> Set[str]:
        """
        Returns all of the non-terminals that can produce epsilon.
        """
        return self.__ent

    def first_sets(self) -> Dict[str, Set[str]]:
        """
        Returns all of the first sets in the grammar.

        :returns: A dictionary mapping each non-terminal to a set of terminals
        """

        ret = {}
        for nt in self.nonterms():
            ret[nt] = set()
        # treat terminals as having themselves in the first set.
        for t in self.terminals():
            ret[t] = {t}
        epsilons = self.epsilon_nonterms()

        # while the grammar is changing.
        # a non recursive loop prevents this from choking on left recursive grammars
        while True:
            updated = False
            for nt, prod in self:
                # go along this production until we hit a token that can't produce epsilon
                for token in prod:
                    tmp = len(ret[nt])

                    # the current nt should include the first set of this token
                    ret[nt] |= ret[token] - {"#"}

                    # if the length of this set changed, set updated to true
                    updated |= len(ret[nt]) != tmp

                    # stop if this token cannot produce epsilon
                    if token not in epsilons:
                        break
                else:
                    ret[nt] |= {"#"}

            # when there are no longer any changes to make
            if not updated:
                # return the dictionary minus the terminals
                return {x: ret[x] for x in ret if x not in self.terminals()}

    def follow_sets(self) -> Dict[str, Set[str]]:
        """
        Returns all of the follow sets in the grammar.

        :returns: A dictionary mapping each non-terminal to a set of terminals
        """

        # get first sets, add our terminals back in
        fs = self.first_sets()
        fs.update({x: {x} for x in self.terminals()})

        epsilons = self.epsilon_nonterms()

        ret = {}
        for nt in self.nonterms():
            ret[nt] = set()
        # start symbol can always be followed by dollar sign
        ret[self.start()] = {"$"}

        # while the set is changing
        while True:
            updated = False

            def update(s1: Set[str], s2: Set[str]) -> bool:
                mpt = len(s1)
                s1 |= s2
                return len(s1) != mpt

            for nt, prod in self:
                # tmp is what can follow the current symbol
                tmp = ret[nt]
                for token in reversed(prod):
                    # if the token is a nonterm
                    if token in self.nonterms():
                        # the follow set of that nonterm includes tmp
                        updated |= update(ret[token], tmp)
                    # if the token can produce epsilon
                    if token in epsilons:
                        # tmp should include this token's first set, minus epsilon
                        tmp |= fs[token] - {"#"}
                    else:
                        # forget about what we had earlier; tmp is now the first set of the current token
                        tmp = fs[token]
            # if the set didn't change
            if not updated:
                # stop
                return ret

    def lex(self, ip: Iterable[str], spcl: Dict[str, str] = None) -> Sequence[Tuple[str, str]]:
        """
        Produces a sequence of terminals out of a raw string.

        :param ip: An iterable of lines to lex.
        :param spcl: Special rules to match.
        These will substitute given regexes for tokens in the CFG instead of matching the text literally.
        For example:
        {
            "ID": "[a-zA-Z]+"
            "NUM": "\\d+"
        }

        :returns: [(terminal in cfg, raw token)...]
        """

        # cannot have mutable default arguments
        if spcl is None:
            spcl = {}

        # for each string, produce a regex
        spcl = {x: re.compile(spcl[x]) for x in spcl}

        # produce a list of tokens to check, exclude any specials as we check those later
        terms = set(self.terminals()) - set(spcl)

        ret: List[Tuple[str, str]] = []
        for line in ip:
            line = line.strip()
            # while there are stil tokens to be read
            while line != "":
                longest: Tuple[str, str] = ("", "")
                # for each terminal, check if the line starts with that terminal
                for s in terms:
                    if line.startswith(s):
                        # if so, set longest to the longer of the two tokens
                        longest = (s, s) if len(s) > len(longest[1]) else longest
                # now check specials
                for name in spcl:
                    # match the beginning of the string with the regex
                    r = spcl[name].match(line, 0)
                    if r is not None:
                        # set the longer of the two tokens
                        longest = (name, r[0]) if len(r[0]) > len(longest[1]) else longest
                # if we matched nothing, throw
                if longest[0] == "":
                    raise CFGException("Invalid token starting with \"" + line + "\"")
                # save the token we read
                ret.append(longest)
                # now get rid of the token we just read from the line
                line = line[len(longest[1]):].strip()
        return ret

    """
    Returns true if a non-terminal is in the grammar.
    """
    def __contains__(self, nt: str) -> bool:
        return nt in self.__rules

    """
    Returns true if two grammars are equivalent.
    """
    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return False
        # if hash(self) == hash(other):
        #    return True
        return self.__rules == other.__rules

    def __hash__(self):
        return self.__hash

    """
    Gets the rules for a given non-terminal.
    """
    def __getitem__(self, nt: str) -> Nonterm:
        return self.__rules[nt]

    """
    Iterates producing (nonterm, rule) for each rule in each nonterm.
    """
    def __iter__(self) -> Iterator[Tuple[str, Sequence[str]]]:
        for nt in self.nonterms():
            for prod in self[nt]:
                yield (nt, prod)

    """
    Returns the amount of nonterms in the grammar.
    """
    def __len__(self) -> int:
        return len(self.__rules)

    """
    Converts the grammar to a string.
    The first rule is always the start symbol.
    """
    def __str__(self) -> str:
        return reduce(lambda a, v: a + "\n" + str(v), [self[nt] for nt in self.nonterms()], "")[1:]
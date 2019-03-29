from functools import reduce
from copy import deepcopy
import itertools
from typing import Callable, Dict, List, Sequence, Set, Tuple, TypeVar


class Grammar:
    __rules: Dict[str, Set[Tuple[str]]] = {}
    __start: str = ""

    __T = TypeVar("__T")

    """
    Internal method. Do not use outside of class
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
        # 0 represents "not in the set", 1 represents "in the set
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
    Internal method. Do not use outside of class
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

    @staticmethod
    def __first(fn: Callable[[__T], bool], c: Sequence[__T]) -> int:
        for i in range(len(c)):
            if fn(c[i]):
                return i
        return -1

    @staticmethod
    def __lex_rhs(rhs: str) -> Tuple[str]:
        ret: List[str] = []
        cur: str = ""
        quote = False
        escape = False
        for c in rhs + " ":
            if escape:
                cur += c
                escape = False
                continue
            if c == " ":
                if not quote:
                    if cur.strip() != "":
                        ret.append(cur)
                    cur = ""
                else:
                    cur += c
                continue
            if c == "\"":
                cur += c
                quote = not quote
                continue
            if c == "\\":
                escape = True
                continue
            cur += c
        if quote:
            raise Exception("Missing closing quote")
        if escape:
            raise Exception("Escape at end of string")
        return tuple(ret)

    def __init__(self, cfg: Sequence[str] = ()):
        for rule in cfg:
            # split name of rule and its right hand side
            a = [x.strip() for x in rule.split("->")]
            if len(a) < 2:
                raise Exception("\"->\" not found in rule \"" + rule + "\"")
            if len(a) > 2:
                raise Exception("Multiple \"->\" found in rule \"" + rule + "\"")

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

        self.__start = cfg[0].split("->")[0].strip() if len(cfg) > 0 else ""

    def __first_set(self, r: str, start: str, first: bool) -> Set[str]:
        ret: Set[str] = set()
        if r == start and not first:
            return set()
        if r not in self:
            return {r}
        for rule in self.__rules[r]:
            c = rule[0]
            if c in self.__rules:
                ret = ret.union(self.__first_set(c, start, False))
            else:
                ret.add(c)
        return ret

    def remove_epsilon(self):
        def add_new_start():
            for a in self.__rules:
                for b in self.__rules[a]:
                    if self.__start in b:
                        szero = self.__start + "0"
                        self.__rules[szero] = {(self.__start,)}
                        self.__start = szero
                        return

        add_new_start()
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

    def remove_recursion(self):
        rules_iter: Sequence[str] = list(self.__rules)
        for nt1 in rules_iter:
            nt1: str = nt1
            for nt2 in rules_iter:
                nt2: str = nt2
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

    def first_set(self, r: str) -> Set[str]:
        return self.__first_set(r, r, True)

    def follow_set(self, r: str) -> Set[str]:
        ret: Set[str] = set()
        if r not in self:
            return {"$"}
        if r == self.__start:
            ret.add("$")
        for rule in self:
            for production in self.__rules[rule]:
                indexes = self.__indices(production, r)
                for index in indexes:
                    rem = list(production[index + 1:])
                    cur = set()
                    hit = False
                    while len(rem) > 0:
                        fs = self.first_set(rem[0])
                        cur |= fs
                        if "#" not in fs:
                            hit = True
                            break
                        rem = rem[1:]
                    if not hit:
                        cur |= self.follow_set(rule)
                    if "#" in cur:
                        cur.remove("#")
                    ret |= cur
        return ret

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

    def __getitem__(self, rule: str):
        return self.__rules[rule]

    def __iter__(self):
        x = self.__start
        y = [x for x in self.__rules if x != self.__start]
        return iter([x] + y)

    def __len__(self):
        return len(self.__rules)

    def __str__(self):
        return reduce(lambda a, v: a + "\n" + v[0] + " -> " + reduce(lambda d, e: d + " | " + reduce(lambda b, c: b + " " + (c if c != "#" else "Ɛ"), e, "")[1:], v[1], "")[3:], [(x, self.__rules[x]) for x in self], "")[1:]


def main():
    x = Grammar([
        "E -> T E’",
        "E’ -> + T E’ | #",
        "T -> F T’",
        "T’ -> * F T’ | #",
        "F -> ( E ) | id"])
    print(x)
    print()
    for rule in x:
        print(rule + ": " + str(x.first_set(rule)))
    print()
    for rule in x:
        print(rule + ": " + str(x.follow_set(rule)))


if __name__ == '__main__':
    main()

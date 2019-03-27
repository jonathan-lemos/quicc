from functools import reduce
from copy import deepcopy
import itertools
from typing import Callable, Dict, List, Sequence, Set, Tuple, TypeVar


T = TypeVar("T")


def first(fn: Callable[[T], bool], c: Sequence[T]) -> int:
    for i in range(len(c)):
        if fn(c[i]):
            return i
    return -1


def split_seq(l: Sequence[T], e: T) -> List[Sequence[T]]:
    indicies = []
    output = []
    for i in range(len(l)):
        if l[i] == e:
            indicies.append(i)
    itmp = 0
    for index in indicies:
        output.append(l[itmp:index])
        output.append(l[index:index + 1])
        itmp = index + 1
    return output


def epsilon_iter(l: Tuple[str], s: str) -> List[Tuple[str]]:
    bitstrings = ["".join(seq) for seq in itertools.product("01", repeat=l.count(s))]
    output = []
    for bs in bitstrings:
        tmp = []
        ctr = 0
        for c in l:
            if c != s:
                tmp.append(c)
            else:
                if bs[ctr] == "1":
                    tmp.append(c)
                ctr += 1
        if len(tmp) == 0:
            output.append(("#",))
        else:
            output.append(tuple(tmp))
    return output


class Ruleset:
    rules: Dict[str, Set[Tuple[str]]] = {}
    start: str = ""

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

            if not a[0] in self.rules:
                self.rules[a[0]] = set()

            # foreach rule in b,
            for r in b:
                # get rid of epsilons unless epsilon is the only member of that rule
                c = tuple(x for x in r.split() if len(r.split()) == 1 or x != "#")
                if len(c) == 0:
                    raise Exception("Cannot have empty rules in CFG rule \"" + r + "\"")
                # add it to the list
                self.rules[a[0]].add(c)

        self.start = cfg[0].split("->")[0].strip() if len(cfg) > 0 else ""

    def remove_epsilon(self):
        s_old = self.start

        def add_new_start():
            for a in self.rules:
                for b in self.rules[a]:
                    if self.start in b:
                        szero = self.start + "0"
                        self.rules[szero] = {(self.start,)}
                        self.start = szero
                        return

        add_new_start()
        rules_iter = list(self.rules)
        for _ in rules_iter:
            for nt1 in rules_iter:
                nt1: str = nt1
                if len([x for x in self.rules[nt1] if x == ('#',)]) == 0:
                    continue
                for nt2 in rules_iter:
                    nt2: str = nt2
                    eps = filter(lambda x: x[1] > 0, [(x, x.count(nt1)) for x in self.rules[nt2]])
                    for rule in eps:
                        new = epsilon_iter(rule[0], nt1)
                        for x in new:
                            self.rules[nt2].add(x)
        for nt in rules_iter:
            if nt == self.start:
                continue
            if ("#",) in self.rules[nt]:
                self.rules[nt].remove(("#",))

    def remove_recursion(self):
        rules_iter = list(self.rules)
        for nt1 in rules_iter:
            nt1: str = nt1
            for nt2 in rules_iter:
                nt2: str = nt2
                cur_rules = deepcopy(self.rules[nt1])
                for rule in cur_rules:
                    rule: Tuple[str] = rule
                    index = first(lambda x: x != nt2, rule)
                    if index == -1:
                        index = len(rule)
                    if index > 0:
                        self.rules[nt1].remove(rule)
                        for r in self.rules[nt2]:
                            self.rules[nt1].add(tuple((list(r) * index) + list(rule[index:])))
            self.remove_dlr(nt1)
        for nt in rules_iter:
            rules = deepcopy(self.rules[nt])
            for rule in rules:
                if '#' in rule and len(rule) > 1:
                    self.rules[nt].remove(rule)
                    newt = tuple([x for x in rule if x != "#"])
                    self.rules[nt].add(newt)

    def remove_dlr(self, rule: str):
        new_rule = set()

        def f(y): return y != rule

        lrec: List[Tuple[str, Tuple[str]]] = [(x[:first(f, x)], x[first(f, x):]) for x in self.rules[rule] if first(f, x) != -1 and first(f, x) > 0]
        notlrec: List[Tuple[str]] = [x for x in self.rules[rule] if first(f, x) == 0]
        ruleprime = rule + "'"

        if len(lrec) == 0:
            return

        for n in notlrec:
            new_rule.add(tuple(list(n) + [ruleprime]))

        new_rule_prime = {("#",)}

        for a, b in lrec:
            new_rule_prime.add(tuple(list(a)[1:] + list(b) + [ruleprime]))

        self.rules[rule] = new_rule
        self.rules[ruleprime] = new_rule_prime

    def __contains__(self, rule: str):
        return rule in self.rules

    def __len__(self):
        return len(self.rules)

    def __str__(self):
        x = self.rules[self.start]
        y = [(a, b) for a, b in self.rules.items() if a != self.start]

        def f(a, c): return a + " | " + reduce(lambda b, e: b + " " + e, c).replace("#", "Ɛ")

        ret = self.start + " -> " + reduce(f, x, "")[2:]
        for d in y:
            ret += "\n" + d[0] + " -> " + reduce(f, d[1], "")[2:]
        return ret


def main():
    # x = Ruleset(["S -> A B w", "A -> X m", "X -> S p | b", "B -> a"])
    # x.remove_recursion()
    x = Ruleset(["S -> A bc A de | A", "A -> S x | #"])
    print(str(x))
    print()
    x.remove_recursion()
    print(str(x))
    print()
    x.remove_epsilon()
    print(str(x))


if __name__ == '__main__':
    main()

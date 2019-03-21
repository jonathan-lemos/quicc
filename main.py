from functools import reduce
from typing import Callable, Dict, List, Set, Tuple, TypeVar


T = TypeVar("T")

# first is the set of rules (str -> Set[Tuple[str]])
# second is the start symbol
cfg_type = Tuple[Dict[str, Set[Tuple[str]]], str]


def first(fn: Callable[[T], bool], c: List[T]) -> int:
    for i in range(len(c)):
        if fn(c[i]):
            return i
    return -1


def cfg_tostring(ip: cfg_type) -> str:
    x = ip[0][ip[1]]
    y = [(a, b) for a, b in ip[0].items() if a != ip[1]]

    def f(a, c): return a + " | " + reduce(lambda b, e: b + " " + e, c).replace("#", "Ɛ")

    ret = ip[1] + " -> " + reduce(f, x, "")[2:]
    for d in y:
        ret += "\n" + d[0] + " -> " + reduce(f, d[1], "")[2:]
    return ret


# Input for the cfg must be as follows:
# S -> 0 S 0 | 1 S 1 | A | #
# pound sign = epsilon
# any distinct token must be seperated by whitespace
def parse_cfg(ip: List[str]) -> cfg_type:
    ret: Dict[str, Set[Tuple[str]]] = {}
    for s in ip:
        # split name of rule and its right hand side
        a = [x.strip() for x in s.split("->")]
        if len(a) < 2:
            raise Exception("\"->\" not found in rule \"" + s + "\"")
        if len(a) > 2:
            raise Exception("Multiple \"->\" found in rule \"" + s + "\"")

        # split by "|"
        b = [x.strip() for x in a[1].split("|")]
        if len(b) == 0:
            raise Exception("Cannot have empty right hand in CFG")

        if not a[0] in ret:
            ret[a[0]] = set()

        # foreach rule in b,
        for rule in b:
            # get rid of epsilons unless epsilon is the only member of that rule
            c = tuple(x for x in rule.split() if len(rule.split()) == 1 or x != "#")
            if len(c) == 0:
                raise Exception("Cannot have empty rules in CFG rule \"" + s + "\"")
            # add it to the list
            ret[a[0]].add(c)

    return ret, ip[0].split("->")[0].strip()


# removes indirect left recursion
def remove_ilr(ip: cfg_type) -> cfg_type:
    productions: Dict[str, Set[Tuple[str]]] = ip[0]
    ret: Dict[str, Set[Tuple[str]]] = {}
    for nt1 in productions:
        nt1: str = nt1
        for nt2 in productions:
            nt2: str = nt2
            new: Set[Tuple[str]] = set()
            for rule in productions[nt1]:
                rule: Tuple[str] = rule
                index = first(lambda x: x != nt1, list(rule))
                if index == -1:
                    raise Exception("Cannot have production of only itself in a CFG (\"" + nt1 + "\"")
                if index > 0:
                    for rhs in productions[nt2]:
                        new.add(tuple(list(rhs) + list(rule[index:])))
                else:
                    new.add(rule)
            if nt1 not in ret:
                ret[nt1] = new
            else:
                for e in new:
                    ret[nt1].add(e)
    return ret, ip[1]


# remove direct left recursion
def remove_dlr(ip: cfg_type) -> cfg_type:
    productions: Dict[str, Set[Tuple[str]]] = ip[0]
    ret: Dict[str, Set[Tuple[str]]] = {}
    for nt in productions:
        nt: str = nt
        ret[nt] = set()

        def f(y): return y != nt

        lrec: List[Tuple[str, Tuple[str]]] = [(x[:first(f, list(x))], x[first(f, list(x)):]) for x in productions[nt] if first(f, list(x)) != -1 and first(f, list(x)) > 0]
        notlrec: List[Tuple[str]] = [x for x in productions[nt] if first(f, list(x)) == 0]
        ntp = nt + "'"

        for n in notlrec:
            ret[nt].add(tuple(list(n) + [ntp]))

        ret[ntp] = {("#",)}

        for a, b in lrec:
            ret[ntp].add(tuple(list(b) + [a]))
    return ret, ip[1]


def main():
    x = parse_cfg(["S -> S A | B", "A -> a", "B -> b"])
    y = remove_dlr(x)
    print(cfg_tostring(x))


if __name__ == '__main__':
    main()

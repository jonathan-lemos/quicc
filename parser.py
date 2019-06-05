from grammar import Grammar
from collections import deque
from typing import Callable, Deque, Dict, FrozenSet, Iterable, Iterator, List, Set, Tuple, Sequence, Union
from copy import copy


class ItemException(Exception):
    pass


class ParseException(Exception):
    pass


def lookahead(prod: Sequence[str], dotpos: int, grammar: Grammar) -> Set[str]:
    if dotpos >= (len(prod) - 1):
        return {"$$"}

    epsilons = grammar.epsilon_nonterms()
    nonterms = grammar.nonterms()
    ret = set()
    nt_passed = set()
    stk = deque()
    stk.append(prod[dotpos + 1:])

    while len(stk) > 0:
        cur = stk.popleft()
        hit = False
        for token in cur:
            if token in nonterms:
                if token in nt_passed:
                    if token in epsilons:
                        continue
                    else:
                        hit = True
                        break
                else:
                    nt_passed.add(token)
                    for prod in grammar[token]:
                        stk.append(prod)
            else:
                ret.add(token)
            if token not in epsilons:
                hit = True
                break
        if not hit:
            ret.add("$$")

    return ret


class Item:
    __nt: str
    __prod: Sequence[str]
    __follow: Set[str]
    __dotpos: int
    __hash: int

    def nt(self):
        return self.__nt

    def prod(self):
        return self.__prod

    def follow(self):
        return self.__follow

    def dotpos(self):
        return self.__dotpos

    def current(self):
        return self.__prod[self.__dotpos]

    def advanced(self):
        return Item(self.__nt, self.__prod, self.__follow, self.__dotpos + 1)

    def is_reduce(self):
        return self.__dotpos >= len(self.__prod)

    def closure(self, grammar: Grammar) -> Sequence["Item"]:
        ret: List["Item"] = []
        hit: Set["Item"] = set()
        q: Deque["Item"] = deque([self])
        nonterms = set(grammar.nonterms())
        lookahead_buf: Dict[Sequence[str], Set[str]] = {}

        parent_follows = {self: lookahead(self.prod(), self.dotpos(), grammar)}
        if "$$" in parent_follows[self]:
            parent_follows[self] -= {"$$"}
            parent_follows[self] |= self.__follow

        while len(q) > 0:
            n = q.popleft()
            if n in ret:
                continue
            ret.append(n)
            hit.add(n)
            if n.is_reduce():
                continue
            sym = n.current()
            if sym in nonterms:
                for prod in grammar[sym]:
                    tmp = Item(sym, prod, parent_follows[n], 0)
                    q.append(tmp)

                    if prod in lookahead_buf:
                        lh = copy(lookahead_buf[prod])
                    else:
                        lh = lookahead(prod, 0, grammar)
                        lookahead_buf[prod] = copy(lh)

                    if "$$" in lh:
                        lh -= {"$$"}
                        lh |= parent_follows[n]
                    parent_follows[tmp] = lh
        return tuple(ret)

    def __hash__(self):
        return self.__hash

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return self.__nt == other.__nt and self.__prod == other.__prod and self.__follow == other.__follow and self.__dotpos == other.__dotpos

    def __init__(self, nt: str, prod: Sequence[str], follow: Set[str], dotpos: int):
        self.__nt = nt
        self.__prod = prod
        self.__follow = follow
        self.__dotpos = dotpos
        self.__hash = hash((self.__nt, self.__prod, tuple(sorted(self.__follow)), self.__dotpos))

    def __str__(self):
        return self.__nt + " -> " + " ".join(self.__prod[0:self.__dotpos]) + " . " + " ".join(self.__prod[self.__dotpos:]) + " {" + ",".join(self.__follow) + "}"


def resolve_shift(i1: Item, i2: Item) -> Item:
    if i1.is_reduce():
        return i2
    return i1


def resolve_reduce(i1: Item, i2: Item) -> Item:
    if i2.is_reduce():
        return i2
    return i1


def resolve_throw(i1: Item, i2: Item) -> Item:
    if i1.is_reduce() and i2.is_reduce():
        raise ItemException("reduce/reduce conflict (\"" + str(i1) + "\", \"" + str(i2) + "\")")
    raise ItemException("shift/reduce conflict (\"" + str(i1) + "\", \"" + str(i2) + "\")")


class ItemSet:
    __items: Sequence[Item]
    __shift: Dict[str, Tuple[int, Item]]
    __reduce: Dict[str, Item]
    __hash: int

    @staticmethod
    def generate(base: Sequence[Item], grammar: Grammar, resolver: Callable[[Item, Item], Item] = resolve_throw) -> Sequence["ItemSet"]:
        ret: List["ItemSet"] = [ItemSet(base, {}, {})]
        hit: Dict[Sequence[Item], int] = {base: 0}

        i = 0
        while i < len(ret):
            for item in ret[i]:
                if item.is_reduce():
                    for char in item.follow():
                        if char in ret[i].__reduce and ret[i].__reduce[char].nt() != item.nt():
                            ret[i].__reduce[char] = resolver(ret[i].__reduce[char], item)
                        if char in ret[i].__shift:
                            res = resolver(ret[i].__shift[char][1], item)
                            if res.is_reduce():
                                del ret[i].__shift[char]
                                ret[i].__reduce[char] = item
                            else:
                                # shift is already in correct spot
                                pass
                        ret[i].__reduce[char] = item
                else:
                    char = item.current()
                    if char in ret[i].__reduce:
                        res = resolver(ret[i].__reduce[char], item)
                        if res.is_reduce():
                            # do nothing with the current shift
                            continue
                        else:
                            del ret[i].__reduce[char]
                            # now deal with the shift

                    target = item.advanced().closure(grammar)

                    if char in ret[i].__shift:
                        target_ind = ret[i].__shift[char][0]

                        tmp = list(ret[target_ind].__items)
                        tmpset = set(tmp)
                        for x in target:
                            if x not in tmpset:
                                tmp.append(x)
                                tmpset.add(x)

                        ret[target_ind].__items = tuple(tmp)
                        target = ret[target_ind].__items
                        hit[target] = target_ind

                    if target not in hit:
                        ret.append(ItemSet(target, {}, {}))
                        hit[target] = len(ret) - 1
                    ret[i].__shift[char] = (hit[target], item)
            i += 1
        for itemset in ret:
            itemset.__calc_hash()
        return ret

    def reduce(self):
        return self.__reduce

    def shift(self):
        return self.__shift

    def __calc_hash(self):
        self.__hash = hash(self.__items) + hash(tuple(self.__shift.items())) + hash(tuple(self.__reduce.items()))

    def __init__(self, items: Sequence[Item], shift: Dict[str, Tuple[int, Item]], reduce: Dict[str, Item]):
        self.__items = items
        self.__shift = shift
        self.__reduce = reduce

    def __iter__(self) -> Iterator[Item]:
        return iter(self.__items)

    def __hash__(self):
        return self.__hash

    def __eq__(self, other):
        if not isinstance(other, ItemSet):
            return False
        return self.__items == other.__items and self.__shift == other.__shift and self.__reduce == other.__reduce

    def __str__(self) -> str:
        vdict = {x[1]: x[0] for x in self.__shift.values()}

        ret = ""
        for item in self:
            ret += str(item) + " "
            if item.is_reduce():
                ret += "(R)"
            elif item not in vdict:
                ret += "(??)"
            else:
                ret += "(S" + str(vdict[item]) + ")"
            ret += "\n"
        return ret.strip()


class ASTNode:
    __rule: str
    __children: Sequence[Union[Tuple[str, str], "ASTNode"]]

    def __init__(self, rule: str, children: Sequence[Union[Tuple[str, str], "ASTNode"]]):
        self.__rule = rule
        self.__children = children

    def rule(self) -> str:
        return self.__rule

    def __iter__(self) -> Iterator[Union[Tuple[str, str], "ASTNode"]]:
        return iter(self.__children)


class LR1Parser:
    __sets: Sequence[ItemSet]
    __grammar: Grammar

    def __init__(self, grammar: Grammar, resolver: Callable[[Item, Item], Item]):
        self.__grammar = grammar
        old_start = grammar.start()
        new_start = old_start + "'"
        new_start_rule = new_start + " -> " + old_start
        g = Grammar([new_start_rule] + str(grammar).split("\n"))
        start_item = Item(new_start, (old_start,), {"$"}, 0)
        self.__sets = ItemSet.generate(start_item.closure(g), g, resolver)

    def parse(self, arg: Union[str, Sequence[Tuple[str, str]]]):
        if isinstance(arg, str):
            arg = self.__grammar.lex([arg])
        arg: Sequence[Tuple[str, str]] = arg

        triples: Deque[Tuple[str, str]] = deque(arg)
        triples.append(("$", "$"))

        stack: Deque[Union[str, int]] = deque(["$", 0])

        while True:
            look, raw = triples[0]
            state: int = stack[len(stack) - 1]

            if look in self.__sets[state].shift():
                triples.popleft()
                stack.append(look)
                stack.append(self.__sets[state].shift()[look][0])
            elif look in self.__sets[state].reduce():
                item = self.__sets[state].reduce()[look]
                for x in reversed(item.prod()):
                    if len(stack) < 3:
                        raise ParseException("Cannot reduce on stack without at least 3 elements")
                    if not isinstance(stack.pop(), int):
                        raise ParseException("Internal error: expected to pop state, but popped token was not of type int")
                    tmp = stack.pop()
                    if tmp != x:
                        raise ParseException("Internal error: popped token \"" + tmp + "\" does not match expected token \"" + x + "\"")
                state = stack[len(stack) - 1]
                if item.nt() not in self.__sets[state].shift():
                    raise ParseException("Internal error: reduced item set does not have transition for \"" + item.nt() + "\"")
                if item.nt() == self.__grammar.start() and look == "$":
                    return
                stack.append(item.nt())
                stack.append(self.__sets[state].shift()[item.nt()][0])
            elif "#" in self.__sets[state].shift():
                stack.append("#")
                stack.append(self.__sets[state].shift()["#"][0])
            else:
                raise ParseException("No transition defined at state " + str(state) + " for symbol " + str(look))

    def __str__(self) -> str:
        return "\n".join(str(x[0]) + ":\n" + str(x[1]) + "\n" for x in enumerate(self.__sets)).strip()

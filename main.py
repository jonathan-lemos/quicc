from grammar import Grammar
from collections import deque
from typing import Deque, Dict, Iterator, List, Set, Tuple, Sequence, Union
import cProfile


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
    nthit = set()
    stk = deque()
    stk.append(prod[dotpos + 1:])

    while len(stk) > 0:
        cur = stk.popleft()
        hit = False
        for token in cur:
            if token in nonterms:
                if token in nthit:
                    hit = True
                    break
                else:
                    nthit.add(token)
                    for nt, p in filter(lambda x: x[0] == token, grammar):
                        stk.append(p)
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
        ret: Set["Item"] = set()
        q: Deque["Item"] = deque([self])
        nonterms = set(grammar.nonterms())

        parent_follows = {self.__prod: self.__follow}

        while len(q) > 0:
            n = q.popleft()
            if n in ret:
                continue
            ret.add(n)
            if n.is_reduce():
                continue
            sym = n.current()
            if sym in nonterms:
                for prod in grammar[sym]:
                    lh = lookahead(prod, n.dotpos(), grammar)
                    if "$$" in lh:
                        lh -= {"$$"}
                        lh |= parent_follows[n.prod()]
                    q.append(Item(sym, prod, parent_follows[n.prod()], 0))
                    parent_follows[prod] = lh
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
        self.__hash = hash(self.__nt) + hash(self.__prod) + hash(tuple(self.__follow)) + self.__dotpos

    def __str__(self):
        return self.__nt + " -> " + " ".join(self.__prod[0:self.__dotpos]) + " . " + " ".join(self.__prod[self.__dotpos:]) + " {" + ",".join(self.__follow) + "}"


class ItemSet:
    __items: Sequence[Item]
    __shift: Dict[str, Tuple[int, Item]]
    __reduce: Dict[str, Item]
    __hash: int

    @staticmethod
    def generate(base: Sequence[Item], grammar: Grammar) -> Sequence["ItemSet"]:
        ret: List["ItemSet"] = []
        hit: Dict[Sequence[Item], int] = {base: 0}
        setup: Set[Sequence[Item]] = {base}

        q: Deque[Sequence[Item]] = deque([base])
        while len(q) > 0:
            cur = q.popleft()
            ind = len(ret)
            if cur in setup:
                continue
            setup.add(cur)
            hit[cur] = ind
            ret.append(ItemSet(cur, {}, {}))

            for item in cur:
                if item.is_reduce():
                    for char in item.follow():
                        if char in ret[ind].__reduce:
                            raise ItemException("reduce/reduce conflict")
                        if char in ret[ind].__shift:
                            raise ItemException("shift/reduce conflict")
                        ret[ind].__reduce[char] = item


    def reduce(self):
        return self.__reduce

    def shift(self):
        return self.__shift

    """
    def __init__(self, base: Sequence[Item], grammar: Grammar, base_so_far: Dict[Sequence[Item], "ItemSet"]):
        self.__items = base
        self.__shift = {}
        self.__reduce = {}
        base_so_far[base] = self
        for item in base:
            if item.is_reduce():
                for char in item.follow():
                    if char in self.__reduce:
                        raise ItemException("reduce/reduce conflict (" + char + " -> (" + str(self.__reduce[char]) + ", " + str(item) + "))")
                    if char in self.__shift:
                        raise ItemException("shift/reduce conflict (" + char + " -> (" + str(self.__shift[char]) + ", " + str(item) + "))")
                    self.__reduce[char] = item
            else:
                char = item.current()
                if char in self.__reduce:
                    raise ItemException("shift/reduce conflict (" + char + " -> (" + str(self.__reduce[char]) + ", " + str(item) + "))")
                if char in self.__shift:
                    raise ItemException("shift/shift conflict (" + char + " -> (" + str(self.__shift[char]) + ", " + char + "))")
                tmp = item.advanced().closure(grammar)
                if tmp in base_so_far:
                    self.__shift[char] = base_so_far[tmp]
                else:
                    self.__shift[char] = ItemSet(item.advanced().closure(grammar), grammar, base_so_far)
        self.__hash = hash(self.__items) + hash(tuple(self.__shift.items())) + hash(tuple(self.__reduce.items()))
    """

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
        ilist: List["ItemSet"] = [self]
        idict: Dict["ItemSet", int] = {self: 0}
        q: Deque["ItemSet"] = deque([self])

        while len(q) > 0:
            cur = q.popleft()
            for itemset in cur.__shift.values():
                if itemset not in idict:
                    idict[itemset] = len(ilist)
                    ilist.append(itemset)
                    q.append(itemset)

        def item2string(x: Item, shift: Dict[str, "ItemSet"], xdict: Dict["ItemSet", int]):
            if x.is_reduce():
                return str(x) + " (R)"
            else:
                return str(x) + " (S" + str(xdict[shift[x.current()]]) + ")"

        s = ""
        for i, itemset in enumerate(ilist):
            s += str(i) + ":\n"
            s += "\n".join(item2string(x, itemset.__shift, idict) for x in itemset.__items) + "\n\n"
        return s.strip()


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
    __base: ItemSet
    __grammar: Grammar

    def __init__(self, grammar: Grammar):
        self.__grammar = grammar
        old_start = grammar.start()
        new_start = old_start + "'"
        new_start_rule = new_start + " -> " + old_start
        g = Grammar([new_start_rule] + str(grammar).split("\n"))
        start_item = Item(new_start, (old_start,), {"$"}, 0)
        self.__base = ItemSet(start_item.closure(g), g, {})

    def parse(self, arg: Union[str, Sequence[Tuple[str, str]]]):
        if isinstance(arg, str):
            arg = self.__grammar.lex(arg)
        arg: Sequence[Tuple[str, str]] = arg

        triples: Deque[Tuple[str, str]] = deque(arg)
        triples.append(("$", "$"))

        stack: Deque[Union[str, ItemSet]] = deque(["$", self.__base])
        while True:
            lah = triples[0][0]
            state: ItemSet = stack[len(stack) - 1]
            for follow, item in state.reduce().items():
                if lah == follow:
                    for x in reversed(item.prod()):
                        if len(stack) < 3:
                            raise ParseException("Cannot reduce on stack without at least 3 elements")
                        if not isinstance(stack.pop(), ItemSet):
                            raise ParseException("Internal error: expected to pop state, but popped token was not of type ItemSet")
                        tmp = stack.pop()
                        if tmp != x:
                            raise ParseException("Internal error: popped token \"" + tmp + "\" does not match expected token \"" + x + "\"")
                    state = stack[len(stack) - 1]
                    if item.nt() not in state.shift():
                        raise ParseException("Internal error: reduced item set does not have transition for \"" + item.nt() + "\"")
                    if item.nt() == self.__grammar.start() and lah == "$":
                        return
                    stack.append(item.nt())
                    stack.append(state.shift()[item.nt()])
                    break
            else:
                tok, raw = triples.popleft()
                if tok not in state.shift():
                    raise ParseException("No transition defined for symbol \"" + tok + "\" at the current state")
                stack.append(tok)
                stack.append(state.shift()[tok])

    def __str__(self) -> str:
        return str(self.__base)


def main():
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
    """
    x = Grammar([
        "E -> + T | #",
        "T -> T x | E"
    ])
    y = LR1Parser(x)
    z = 2 + 2


if __name__ == '__main__':
    main()

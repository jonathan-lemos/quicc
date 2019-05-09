from grammar import Grammar
from collections import deque
from typing import Deque, Dict, FrozenSet, Iterable, Iterator, List, Set, Tuple, Sequence, Union
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

    def closure(self, grammar: Grammar) -> Set["Item"]:
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
        return ret

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
        self.__hash = hash(self.__nt) + hash(self.__prod) + hash(tuple(sorted(self.__follow))) + self.__dotpos

    def __str__(self):
        return self.__nt + " -> " + " ".join(self.__prod[0:self.__dotpos]) + " . " + " ".join(self.__prod[self.__dotpos:]) + " {" + ",".join(self.__follow) + "}"


class ItemSet:
    __items: FrozenSet[Item]
    __shift: Dict[str, Tuple[int, Item]]
    __reduce: Dict[str, Item]
    __hash: int

    @staticmethod
    def generate(base: Iterable[Item], grammar: Grammar) -> Sequence["ItemSet"]:
        ret: List["ItemSet"] = [ItemSet(base, {}, {})]
        hit: Dict[FrozenSet[Item], int] = {frozenset(base): 0}

        i = 0
        while i < len(ret):
            for item in ret[i]:
                if item.is_reduce():
                    for char in item.follow():
                        if char in ret[i].__reduce:
                            raise ItemException("reduce/reduce conflict (\"" + str(ret[i].__reduce[char]) + "\", \"" + str(item) + "\")")
                        if char in ret[i].__shift:
                            raise ItemException("shift/reduce conflict (\"" + str(ret[i].__shift[char][1]) + "\", \"" + str(item) + "\")")
                        ret[i].__reduce[char] = item
                else:
                    char = item.current()
                    if char in ret[i].__reduce:
                        raise ItemException("shift/reduce conflict (\"" + str(ret[i].__reduce[char]) + "\", \"" + str(item) + "\")")
                    target = frozenset(item.advanced().closure(grammar))
                    if char in ret[i].__shift:
                        target_ind = ret[i].__shift[char][0]
                        ret[target_ind].__items = frozenset(target.union(target.union(ret[target_ind].__items)))
                        target = frozenset(target.union(target.union(ret[target_ind].__items)))
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

    def __init__(self, items: Iterable[Item], shift: Dict[str, Tuple[int, Item]], reduce: Dict[str, Item]):
        self.__items = frozenset(items)
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
        def shift2string(x: Tuple[int, Item]):
            return str(x[1]) + " (S" + str(x[0]) + ")"

        return "\n".join({shift2string(x) for x in self.__shift.values()} | {str(x) + " (R)" for x in self.__reduce.values()})


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

    def __init__(self, grammar: Grammar):
        self.__grammar = grammar
        old_start = grammar.start()
        new_start = old_start + "'"
        new_start_rule = new_start + " -> " + old_start
        g = Grammar([new_start_rule] + str(grammar).split("\n"))
        start_item = Item(new_start, (old_start,), {"$"}, 0)
        self.__sets = ItemSet.generate(start_item.closure(g), g)

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
        return "\n".join(str(x[0]) + ":\n" + str(x[1]) + "\n" for x in enumerate(self.__sets)).strip()


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
        "simple-expression -> additive-expression RELOP additive-expression | additive-expression",
        "additive-expression -> additive-expression ADDOP term | term",
        "term -> term MULOP factor | factor",
        "factor -> ( expression ) | var | call | NUM",
        "call -> ID ( args )",
        "args -> arg-list | #",
        "arg-list -> arg-list , expression | expression",
    ])
    tokens = x.lex([
        "int main(void) {",
        "   return 0;",
        "}"
    ], {
        "NUM": "[0-9]+\\.[0-9]+|[0-9]+",
        "ID": "[A-Za-z]+",
        "RELOP": "<=|<|>|>=|==|!=",
        "ADDOP": "[+\\-]",
        "MULOP": "[*/]",
    })
    z = x.follow_sets()
    y = LR1Parser(x)
    print(str(y))
    z = 2 + 2


if __name__ == '__main__':
    main()

from grammar import Grammar
from collections import deque
from typing import Deque, Dict, Iterator, List, Set, Tuple, Sequence, Union


class ItemException(Exception):
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
        q: Deque["Item"] = deque([self])
        nonterms = set(grammar.nonterms())

        parent_follows = {self.__prod: self.__follow}

        while len(q) > 0:
            n = q.popleft()
            ret.append(n)
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
        return hash(self.__nt) + hash(self.__prod) + hash(tuple(self.__follow)) + self.__dotpos

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        return self.__nt == other.__nt and self.__prod == other.__prod and self.__follow == other.__follow and self.__dotpos == other.__dotpos

    def __init__(self, nt: str, prod: Sequence[str], follow: Set[str], dotpos: int):
        self.__nt = nt
        self.__prod = prod
        self.__follow = follow
        self.__dotpos = dotpos

    def __str__(self):
        return self.__nt + " -> " + " ".join(self.__prod[0:self.__dotpos]) + " . " + " ".join(self.__prod[self.__dotpos:]) + " {" + ",".join(self.__follow) + "}"


class ItemSet:
    __items: Sequence[Item]
    __shift: Dict[str, "ItemSet"]
    __reduce: Dict[str, str]

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
                    self.__reduce[char] = item.nt()
            else:
                char = item.current()
                if char in self.__shift:
                    raise ItemException("shift/shift conflict (" + char + " -> (" + str(self.__shift[char]) + ", " + char + "))")
                if char in self.__reduce:
                    raise ItemException("shift/reduce conflict (" + char + " -> (" + self.__reduce[char] + ", " + str(item) + "))")
                tmp = item.advanced().closure(grammar)
                if tmp in base_so_far:
                    self.__shift[char] = base_so_far[tmp]
                else:
                    self.__shift[char] = ItemSet(item.advanced().closure(grammar), grammar, base_so_far)

    def __iter__(self) -> Iterator[Item]:
        return iter(self.__items)

    def __str__(self) -> str:
        hit: Set[Sequence[Item]] = set()
        q: Deque["ItemSet"] = deque([self])
        s = ""
        ctr = 0

        while len(q) > 0:
            cur = q.popleft()
            s += str(ctr) + ":\n" + "\n".join(str(x) for x in cur.__items) + "\n\n"
            ctr += 1
            for itemset in self.__shift.values():
                if itemset.__items not in hit:
                    hit.add(itemset.__items)
                    q.append(itemset)
            for sym, follow in self.__reduce.items():
                pass

        return s.strip()



class LR1Parser:
    __base: ItemSet

    def __init__(self, grammar: Grammar):
        old_start = grammar.start()
        new_start = old_start + "'"
        new_start_rule = new_start + " -> " + old_start
        g = Grammar([new_start_rule] + str(grammar).split("\n"))
        start_item = Item(new_start, (old_start,), {"$"}, 0)
        # b = Item("C", ("e", "C"), {"$"}, 1)
        # c = b.closure(g)
        self.__base = ItemSet(start_item.closure(g), g, {})

    def __str__(self) -> str:
        return str(self.__base)


def main():
    x = Grammar([
        "S -> C C",
        "C -> e C | d"
    ])

    a = LR1Parser(x)
    print(str(a))

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
        "ID": "[A-Za-z]+",
        "NUM": "\\d+|\\d\\.\\d+"
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

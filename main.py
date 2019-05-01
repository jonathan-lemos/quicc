from grammar import Grammar
from collections import deque
from typing import Deque, List, Set, Tuple


def lookahead(prod: Tuple[str], dotpos: int, grammar: Grammar) -> Set[str]:
    if dotpos >= (len(prod) - 1):
        return {"$$"}

    epsilons = grammar.epsilon_nonterms()
    index = dotpos + 1
    ret = set()
    stk = deque(prod)

    while len(stk) > 0:
        cur = stk.popleft()
        hit = False
        for token in prod[dotpos:]:
            ret.add(token)
            if token in epsilons:
                hit = True
                break
        if not hit:
            ret.add("#")




class Item:
    __nt: str
    __prod: Tuple[str]
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

    def is_reduce(self):
        return self.__dotpos >= len(self.__prod)

    def closure(self, grammar: Grammar) -> Set["Item"]:
        ret: Set["Item"] = set()
        q: Deque["Item"] = deque([self])
        nonterms = set(grammar.nonterms())
        terms = set(grammar.terminals())

        while len(q) > 0:
            n = q.popleft()
            ret.add(n)
            sym = n.prod()[0]
            if sym in terms:
                for prod in grammar[sym]:
                    q.append(Item(sym, prod, self.follow))
        return ret

    def __init__(self, nt: str, prod: Tuple[str], follow: Set[str], dotpos: int):
        self.__nt = nt
        self.__prod = prod
        self.__follow = follow
        self.__dotpos = dotpos

    def __str__(self):
        return self.__nt + " -> " + " ".join(self.__prod[0:self.__dotpos]) + " . " + " ".join(self.__prod[self.__dotpos:])


class LR1Parser:
    __itemsets: List[Item]

    def __init__(self, g: Grammar):
        pass


def main():
    x = Grammar([
        "S -> C C",
        "C -> e C | d"
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

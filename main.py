import cProfile
from grammar import Grammar
from parser import LR1Parser, resolve_shift


def main():
    x = Grammar([
        "program -> declaration-list",
        "declaration-list -> declaration-list declaration | declaration",
        "declaration -> var-declaration | fun-declaration",
        "var-declaration -> TYPE ID ; | TYPE ID [ NUM ] ;",
        "fun-declaration -> TYPE ID ( params ) compound-stmt",
        "params -> param-list | void",
        "param-list -> param-list , param | param",
        "param -> TYPE ID | TYPE ID [ ]",
        "TYPE -> int | float | void",
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
        "void x(void) {",
        "   if (1 > 0) {"
        "       return;",
        "   } else {",
        "       2 + 2;",
        "   }",
        "}",
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

    y = LR1Parser(x, resolve_shift)
    print(str(y))
    y.parse(tokens)
    z = 2 + 2


if __name__ == '__main__':
    # main()
    cProfile.run("main()", sort='cumtime')

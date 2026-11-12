private import codeql.ucode.AST

query predicate astNodes(AstNode n) { any() }

query predicate literals(Literals l) { any() }

query predicate variables(Variable v) { any() }

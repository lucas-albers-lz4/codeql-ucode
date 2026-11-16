import codeql.ucode.AST
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

private UCODE::AstNode declarationToken(Variable v) {
  exists(UCODE::VariableDeclarator d |
    v.getAstNode() = TVariableDeclarator(d) and result = d.getName()
  )
  or
  exists(UCODE::Identifier id | v.getAstNode() = TIdentifier(id) and result = id)
}

from VariableReadAccess a, UCODE::AstNode d
where a.getName() = "x" and d = declarationToken(a.getVariable())
select a.getLocation().getFile().getBaseName(), a.getLocation().getStartLine(),
  a.getLocation().getStartColumn(), a.getLocation().getEndLine(), a.getLocation().getEndColumn(),
  d.getLocation().getFile().getBaseName(), d.getLocation().getStartLine(),
  d.getLocation().getStartColumn(), d.getLocation().getEndLine(), d.getLocation().getEndColumn(),
  toTreeSitter(a.getAstNode()).getAPrimaryQlClass()

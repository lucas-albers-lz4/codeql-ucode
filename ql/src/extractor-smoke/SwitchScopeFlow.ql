import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

from DataFlow::ExprNode src, DataFlow::ExprNode snk, UCODE::CallExpression call,
  UCODE::Identifier ident
where
  toTreeSitter(src.getExprNode().getAstNode()) = call and
  call.getFunction().(UCODE::Identifier).getValue() = "source" and
  toTreeSitter(snk.getExprNode().getAstNode()) = ident and
  ident.getValue() = "x" and
  src.getLocation().getFile().getBaseName() = "scope.uc" and
  DataFlow::localExprFlow(src.getExprNode(), snk.getExprNode())
select src.getLocation().getStartLine() as sourceLine,
  src.getLocation().getStartColumn() as sourceColumn,
  snk.getLocation().getStartLine() as readLine,
  snk.getLocation().getStartColumn() as readColumn

// Public experimental local-expression flow for the two issue fixtures.
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

from DataFlow::ExprNode src, DataFlow::ExprNode snk, UCODE::Identifier ident
where
  toTreeSitter(snk.getExprNode().getAstNode()) = ident and
  ident.getValue() = "x" and
  src.getLocation().getFile() = snk.getLocation().getFile() and
  src.getLocation().getFile().getBaseName() = ["break.uc", "break_control.uc", "controls.uc"] and
  DataFlow::localExprFlow(src.getExprNode(), snk.getExprNode())
select src.getLocation().getFile().getBaseName() as file,
  src.getLocation().getStartLine() as sourceLine,
  src.getLocation().getStartColumn() as sourceColumn,
  src.getLocation().getEndLine() as sourceEndLine,
  src.getLocation().getEndColumn() as sourceEndColumn,
  snk.getLocation().getStartLine() as readLine,
  snk.getLocation().getStartColumn() as readColumn,
  snk.getLocation().getEndLine() as readEndLine,
  snk.getLocation().getEndColumn() as readEndColumn

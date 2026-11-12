/**
 * @name Expression value-flow regression
 * @description Reports source call to identifier expression flows in the isolated fixture.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/test/expression-flow-regression
 */

import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

from
  DataFlow::ExprNode src, DataFlow::ExprNode snk, UCODE::CallExpression call,
  UCODE::Identifier ident
where
  toTreeSitter(src.getExprNode().getAstNode()) = call and
  call.getFunction().(UCODE::Identifier).getValue() = "source" and
  toTreeSitter(snk.getExprNode().getAstNode()) = ident and
  DataFlow::localExprFlow(src.getExprNode(), snk.getExprNode()) and
  src.getLocation().getFile().getBaseName() = "ssa_pos"
select src,
  src.getLocation().getStartLine().toString() + " -> " + ident.getValue() + ":" +
    snk.getLocation().getStartLine().toString()

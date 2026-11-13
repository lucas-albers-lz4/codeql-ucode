/**
 * @name Return value-flow regression
 * @description Reports source calls reaching callable return nodes.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/test/return-flow-regression
 */

import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

from DataFlow::ExprNode src, DataFlow::ReturnValueNode snk, UCODE::CallExpression call
where
  toTreeSitter(src.getExprNode().getAstNode()) = call and
  call.getFunction().(UCODE::Identifier).getValue() = "source" and
  DataFlow::localFlowStep+(src, snk) and
  src.getLocation().getFile().getBaseName() = "ssa_pos"
select src,
  src.getLocation().getStartLine().toString() + " -> " + snk.getLocation().getStartLine().toString()

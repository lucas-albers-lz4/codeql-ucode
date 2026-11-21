/**
 * Experimental intra-procedural flow trace for receiver controls. The
 * localFlowStep+ closure may include multiple transfers; it does not enforce
 * a one-copy bound. Observation only; no runtime identity or security claim.
 */
import codeql.ucode.AST
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.DataFlow

from
  DataFlow::SsaDefinitionNode source, DataFlow::SsaReadNode receiverRead,
  VariableReadAccess receiverAccess, UCODE::MemberExpression member,
  UCODE::CallExpression call
where
  source.getLocation().getFile().getRelativePath() = "alias-transfer-controls.uc" and
  member = call.getFunction() and
  DataFlow::localFlowStep+(source, receiverRead) and
  receiverRead.getDefinition().getSourceVariable() = receiverAccess.getVariable() and
  receiverRead.getRead().getAstNode() = receiverAccess.getAstNode() and
  toTreeSitter(receiverAccess.getAstNode()) = member.getObject() and
  member.getProperty().getValue() in ["read", "close"]
select source, receiverRead.getRead(), call,
  source.getDefinition().getSourceVariable().getName() + " -> " +
    receiverRead.getDefinition().getSourceVariable().getName() + ":" +
    member.getProperty().getValue() + "@" + member.getLocation().getStartLine().toString()

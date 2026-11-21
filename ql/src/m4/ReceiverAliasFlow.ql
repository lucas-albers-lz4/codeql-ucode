/**
 * Experimental intra-procedural identifier-copy trace for receiver controls.
 * Observation only; no runtime resource identity or security conclusion.
 */
import codeql.ucode.AST
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.DataFlow

from
  DataFlow::SsaDefinitionNode source, DataFlow::SsaReadNode receiverRead,
  VariableReadAccess receiverAccess, UCODE::MemberExpression member
where
  source.getLocation().getFile().getRelativePath() = "alias-transfer-controls.uc" and
  DataFlow::localFlowStep+(source, receiverRead) and
  receiverRead.getDefinition().getSourceVariable() = receiverAccess.getVariable() and
  receiverRead.getRead().getAstNode() = receiverAccess.getAstNode() and
  receiverAccess.getLocation() = member.getObject().getLocation() and
  member.getProperty().getValue() in ["read", "close"]
select source, receiverRead.getRead(), member,
  source.getDefinition().getSourceVariable().getName() + " -> " +
    receiverRead.getDefinition().getSourceVariable().getName() + ":" +
    member.getProperty().getValue() + "@" + member.getLocation().getStartLine().toString()

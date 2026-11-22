/**
 * Experimental source-level observations for one direct variable copy from a
 * source-declared fs popen initializer to a direct read/close receiver. The
 * two local-flow joins are bounded to source -> copy-read -> receiver-read;
 * this is not runtime resource identity, call-target resolution, taint, or a
 * security result. Reassignments are distinguished by SSA write identity.
 */
import codeql.ucode.AST
import codeql.ucode.DataFlow
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs

from
  DataFlow::SsaDefinitionNode source, DataFlow::SsaReadNode receiverRead,
  DataFlow::SsaDefinitionNode copyDefinition, DataFlow::SsaReadNode copyRead,
  UCODE::VariableDeclarator sourceDecl, UCODE::VariableDeclarator copyDecl,
  UCODE::CallExpression initializer, UCODE::CallExpression call,
  VariableReadAccess receiverAccess, UCODE::Identifier receiver,
  UCODE::MemberExpression member, string relation
where
  source.getDefinition().getSourceVariable().getAstNode() = TVariableDeclarator(sourceDecl) and
  source.getCfgNode().getAstNode() = TVariableDeclarator(sourceDecl) and
  initializer = sourceDecl.getValue() and
  sourceDeclaredFsCall(initializer, "popen") and
  member = call.getFunction() and
  receiver = member.getObject() and
  receiverAccess.getAstNode() = TIdentifier(receiver) and
  receiverRead.getRead().getAstNode() = receiverAccess.getAstNode() and
  receiverRead.getDefinition().getSourceVariable() = receiverAccess.getVariable() and
  member.getProperty().getValue() in ["read", "close"] and
  not exists(call.getOptionalChain()) and
  not exists(member.getOptionalChain()) and
  exists(VariableReadAccess copiedFrom, UCODE::Identifier copySource |
    copySource.getParent() = copyDecl and
    copiedFrom.getAstNode() = TIdentifier(copySource) and
    copiedFrom.getVariable() = source.getDefinition().getSourceVariable() and
    copyDefinition.getDefinition().getSourceVariable().getAstNode() = TVariableDeclarator(copyDecl) and
    copyDefinition.getCfgNode().getAstNode() = TVariableDeclarator(copyDecl) and
    receiverRead.getDefinition() = copyDefinition.getDefinition() and
    DataFlow::localFlowStep+(source, copyRead) and
    copyRead.getRead().getAstNode() = copiedFrom.getAstNode() and
    copyRead.getDefinition() = source.getDefinition() and
    DataFlow::localFlowStep+(copyDefinition, receiverRead) and
    relation = "one direct copy to direct receiver"
  )
select sourceDecl, initializer, copyDecl, receiver, call, relation

/**
 * Experimental source-level may-reach observations for one direct variable
 * copy from a source-declared fs popen initializer to a direct read/close
 * receiver. Each local-flow join spans one edge from source -> copy-read ->
 * receiver-read. This is not runtime resource identity, call-target
 * resolution, taint, or a security result. Reassignments are distinguished
 * by SSA write identity.
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
  VariableReadAccess receiverAccess, UCODE::Identifier receiver, UCODE::AstNode copySource,
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
  exists(VariableReadAccess copiedFrom |
    copySource = copyDecl.getValue() and
    toTreeSitter(copiedFrom.getAstNode()) = copySource and
    copiedFrom.getVariable() = source.getDefinition().getSourceVariable() and
    copyDefinition.getDefinition().getSourceVariable().getAstNode() = TVariableDeclarator(copyDecl) and
    copyDefinition.getCfgNode().getAstNode() = TVariableDeclarator(copyDecl) and
    receiverRead.getDefinition() = copyDefinition.getDefinition() and
    DataFlow::localFlowStep(source, copyRead) and
    copyRead.getRead().getAstNode() = copiedFrom.getAstNode() and
    copyRead.getDefinition() = source.getDefinition() and
    DataFlow::localFlowStep(copyDefinition, receiverRead) and
    relation = "one direct copy may reach direct receiver"
  )
select sourceDecl, initializer, copyDecl, receiver, call, relation

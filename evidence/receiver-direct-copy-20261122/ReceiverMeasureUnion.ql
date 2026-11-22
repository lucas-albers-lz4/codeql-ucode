import FsReceiverOrigin
import codeql.ucode.AST
import codeql.ucode.DataFlow
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs

from UCODE::CallExpression call, UCODE::VariableDeclarator decl, UCODE::CallExpression initializer, UCODE::Identifier receiver, string method, string factory
where
  (receiverOrigin(call, decl, initializer, method, factory) and directMember(call, receiver, method))
  or
  exists(
  DataFlow::SsaDefinitionNode source, DataFlow::SsaReadNode receiverRead,
  DataFlow::SsaDefinitionNode copyDefinition, DataFlow::SsaReadNode copyRead,
  UCODE::VariableDeclarator sourceDecl, UCODE::VariableDeclarator copyDecl,
  
  VariableReadAccess receiverAccess, UCODE::AstNode copySource,
  UCODE::MemberExpression member, string relation |
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
  ) and
  sourceDecl = decl and method = member.getProperty().getValue() and factory = "popen"
  )
select call, receiver, decl, initializer, method, factory

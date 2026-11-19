import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs

/** Direct source-declared popen initializer; not a runtime target. */
predicate directMember(UCODE::CallExpression call, UCODE::Identifier receiver, string method) {
  exists(UCODE::MemberExpression member |
    member = call.getFunction() and
    receiver = member.getObject() and
    method = member.getProperty().getValue() and
    method = ["read", "close"] and
    not exists(call.getOptionalChain()) and
    not exists(member.getOptionalChain())
  )
}

private predicate functionBoundary(UCODE::AstNode node) {
  node instanceof UCODE::FunctionDeclaration or
  node instanceof UCODE::FunctionExpression or
  node instanceof UCODE::ArrowFunction or
  node instanceof UCODE::Program
}

private UCODE::AstNode enclosingFunction(UCODE::AstNode node) {
  result = node.getParent+() and
  functionBoundary(result) and
  not exists(UCODE::AstNode inner |
    inner = node.getParent+() and inner.getParent+() = result and functionBoundary(inner)
  )
}

private predicate allowedUse(VariableAccess use, UCODE::VariableDeclarator decl) {
  exists(UCODE::Identifier id |
    use.getAstNode() = TIdentifier(id) and
    enclosingFunction(id) = enclosingFunction(decl) and
    (
      exists(UCODE::CallExpression call | directMember(call, id, _)) or
      exists(UCODE::IfStatement condition | condition.getCondition().getChild() = id)
    )
  )
}

/**
 * A source-provenance observation, deliberately not a library callable,
 * summary, flow edge, runtime method identity or production security result.
 * Reject recognized writes and uses outside a small same-function allowlist.
 * This syntactic guard and the underlying lexical binding are approximations;
 * they do not prove runtime stability or absence of every kind of escape.
 */
predicate receiverOrigin(
  UCODE::CallExpression call, UCODE::VariableDeclarator decl, UCODE::CallExpression initializer,
  string method, string factory
) {
  exists(UCODE::Identifier receiver, VariableReadAccess use, Variable variable |
    directMember(call, receiver, method) and
    use.getAstNode() = TIdentifier(receiver) and
    variable = use.getVariable() and
    variable.getAstNode() = TVariableDeclarator(decl) and
    initializer = decl.getValue() and
    factory = "popen" and
    sourceDeclaredFsCall(initializer, factory) and
    enclosingFunction(call) = enclosingFunction(decl) and
    not exists(VariableWriteAccess write | write.getVariable() = variable) and
    not exists(VariableAccess other |
      other.getVariable() = variable and not allowedUse(other, decl)
    )
  )
}

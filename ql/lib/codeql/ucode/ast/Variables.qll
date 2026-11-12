/**
 * ucode variables from lexical `let`/`const` declarators.
 *
 * Generator leftover `codeql.bicep` imports, ParameterDeclaration/OutputDeclaration,
 * and `getEnclosingCfgScope` are intentionally absent. Name binding uses the nearest lexical block and respects function parameters.
 * SSA uses these accesses at statement-level CFG nodes; it is not
 * interprocedural taint and not a sanitizer model.
 */

private import codeql.Locations
private import AstNodes
private import internal.AstNodes
private import internal.TreeSitter

private predicate variableDecl(AstNode node, string name) {
  exists(UCODE::VariableDeclarator d |
    node = TVariableDeclarator(d) and
    name = d.getName().getValue()
  )
}

/**
 * A variable defined by a lexical declarator.
 */
class Variable extends MkVariable {
  private AstNode node;
  private string name;

  Variable() { this = MkVariable(node, name) }

  string getName() { result = name }

  string toString() { result = "Variable[" + name + "]" }

  AstNode getAstNode() { result = node }

  Location getLocation() { result = node.getLocation() }

  VariableAccess getAnAccess() { result.getVariable() = this }

  string getAPrimaryQlClass() { result = "Variable" }
}

/** Lexical blocks and the program delimit let/const bindings. */
private predicate lexicalScope(UCODE::AstNode scope) {
  scope instanceof UCODE::StatementBlock or scope instanceof UCODE::Program
}

private UCODE::AstNode declarationScope(UCODE::VariableDeclarator d) {
  result = d.getParent+() and
  lexicalScope(result) and
  not exists(UCODE::AstNode inner |
    inner = d.getParent+() and inner.getParent+() = result and lexicalScope(inner)
  )
}

/** A parameter shadows bindings outside the body of its function. */
private predicate parameterBinding(UCODE::AstNode body, string name) {
  exists(UCODE::FunctionExpression f, UCODE::Identifier p |
    body = f.getBody() and p.getParent+() = f.getParameters() and p.getValue() = name
  )
  or
  exists(UCODE::FunctionDeclaration f, UCODE::Identifier p |
    body = f.getBody() and p.getParent+() = f.getParameters() and p.getValue() = name
  )
  or
  exists(UCODE::ArrowFunction f, UCODE::Identifier p |
    body = f.getBody() and
    (p = f.getParameter() or p.getParent+() = f.getParameters()) and
    p.getValue() = name
  )
}

private predicate access(AstNode node, Variable v, string name) {
  exists(UCODE::Identifier ident, UCODE::VariableDeclarator decl, UCODE::AstNode scope |
    v.getAstNode() = TVariableDeclarator(decl) and
    scope = declarationScope(decl) and
    ident.getValue() = name and
    name = v.getName() and
    ident.getParent+() = scope and
    node = TIdentifier(ident) and
    not exists(UCODE::VariableDeclarator d | d.getName() = ident) and
    not exists(UCODE::FormalParameters ps | ident.getParent+() = ps) and
    not exists(UCODE::FunctionDeclaration f | f.getName() = ident) and
    not exists(UCODE::FunctionExpression f | f.getName() = ident) and
    not exists(UCODE::ArrowFunction f | f.getParameter() = ident) and
    not exists(UCODE::VariableDeclarator other, UCODE::AstNode inner |
      other != decl and
      other.getName().getValue() = name and
      inner = declarationScope(other) and
      inner.getParent+() = scope and
      ident.getParent+() = inner
    ) and
    not exists(UCODE::AstNode body |
      parameterBinding(body, name) and
      body.getParent+() = scope and
      ident.getParent*() = body
    )
  )
}

private predicate simpleWrite(UCODE::Identifier ident) {
  exists(UCODE::AssignmentExpression a | a.getLeft() = ident)
}

private predicate modifyingWrite(UCODE::Identifier ident) {
  exists(UCODE::AugmentedAssignmentExpression a | a.getLeft() = ident) or
  exists(UCODE::UpdateExpression u | u.getArgument() = ident)
}

/**
 * An identifier use of a variable.
 */
class VariableAccess extends MkVariableAccess {
  private string name;
  private AstNode node;
  private Variable v;

  VariableAccess() { this = MkVariableAccess(node, v, name) }

  string getName() { result = name }

  AstNode getAstNode() { result = node }

  Variable getVariable() { result = v }

  string toString() { result = "VariableAccess[" + name + "]" }

  Location getLocation() { result = node.getLocation() }

  string getAPrimaryQlClass() { result = "VariableAccess" }
}

class VariableWriteAccess extends VariableAccess {
  VariableWriteAccess() {
    exists(UCODE::Identifier ident |
      this.getAstNode() = TIdentifier(ident) and
      (simpleWrite(ident) or modifyingWrite(ident))
    )
  }

  override string getAPrimaryQlClass() { result = "VariableWrite" }
}

class VariableReadAccess extends VariableAccess {
  VariableReadAccess() {
    exists(UCODE::Identifier ident |
      this.getAstNode() = TIdentifier(ident) and
      not simpleWrite(ident)
    )
  }

  override string getAPrimaryQlClass() { result = "VariableRead" }
}

cached
private module Cached {
  cached
  newtype TVariable =
    MkVariable(AstNode definingNode, string name) { variableDecl(definingNode, name) }

  cached
  newtype TVariableAccess =
    MkVariableAccess(AstNode node, Variable v, string name) { access(node, v, name) }
}

private import Cached

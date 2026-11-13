/**
 * ucode lexical variables, loop bindings, catch parameters, and named formals.
 *
 * Generator leftover `codeql.bicep` imports, ParameterDeclaration/OutputDeclaration,
 * and `getEnclosingCfgScope` are intentionally absent. Name binding uses the nearest lexical block and respects function parameters.
 * SSA uses ordered access-level CFG nodes; it is not
 * interprocedural taint and not a sanitizer model.
 * VariableWriteAccess is the identifier LHS of `=`, augmented
 * assignment, updates, and assignment-form `for-in`. Lexical
 * declarators, parameters, and catch bindings are SSA writes but
 * not VariableWriteAccess.
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
  or
  exists(UCODE::ForInStatement f, UCODE::Identifier id |
    exists(f.getKind()) and
    (id = f.getVariable() or id = f.getKey() or id = f.getValue()) and
    node = TIdentifier(id) and
    name = id.getValue()
  )
  or
  exists(UCODE::ForInAltStatement f, UCODE::Identifier id |
    exists(f.getKind()) and
    (id = f.getVariable() or id = f.getKey() or id = f.getValue()) and
    node = TIdentifier(id) and
    name = id.getValue()
  )
  or
  exists(UCODE::CatchClause c, UCODE::Identifier id |
    id = c.getParameter() and node = TIdentifier(id) and name = id.getValue()
  )
  or
  exists(UCODE::Identifier id |
    namedFormalIdentifier(id) and node = TIdentifier(id) and name = id.getValue()
  )
}

/** Identifier token of a `FormalParameters` child or a bare arrow parameter. */
private predicate formalInParameters(UCODE::FormalParameters ps, UCODE::Identifier id) {
  id = ps.getChild(_)
  or
  exists(UCODE::RestElement rest | rest = ps.getChild(_) and id = rest.getChild())
}

/** Named function or arrow formal. Not a function name. */
private predicate namedFormalIdentifier(UCODE::Identifier id) {
  exists(UCODE::FormalParameters ps | formalInParameters(ps, id))
  or
  exists(UCODE::ArrowFunction f | id = f.getParameter())
}

/** Body that binds uses of a named formal. */
private UCODE::AstNode functionBodyOfFormal(UCODE::Identifier id) {
  exists(UCODE::FunctionExpression f |
    formalInParameters(f.getParameters(), id) and result = f.getBody()
  )
  or
  exists(UCODE::FunctionDeclaration f |
    formalInParameters(f.getParameters(), id) and result = f.getBody()
  )
  or
  exists(UCODE::ArrowFunction f |
    (id = f.getParameter() or formalInParameters(f.getParameters(), id)) and
    result = f.getBody()
  )
}

/**
 * A variable defined by a lexical declarator, loop binding, catch parameter,
 * or named function formal.
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
  scope instanceof UCODE::StatementBlock or
  scope instanceof UCODE::StatementList or
  scope instanceof UCODE::Program
}

private UCODE::AstNode declarationScope(UCODE::VariableDeclarator d) {
  exists(UCODE::ForStatement f | d.getParent() = f.getInitializer() and result = f)
  or
  exists(UCODE::ForAltStatement f | d.getParent() = f.getInitializer() and result = f)
  or
  not exists(UCODE::ForStatement f | d.getParent() = f.getInitializer()) and
  not exists(UCODE::ForAltStatement f | d.getParent() = f.getInitializer()) and
  result = d.getParent+() and
  lexicalScope(result) and
  not exists(UCODE::AstNode inner |
    inner = d.getParent+() and inner.getParent+() = result and lexicalScope(inner)
  )
}

/** A declaration's actual binding scope, including loop-local bindings. */
private UCODE::AstNode bindingScope(Variable v) {
  exists(UCODE::VariableDeclarator d |
    v.getAstNode() = TVariableDeclarator(d) and result = declarationScope(d)
  )
  or
  exists(UCODE::ForInStatement f, UCODE::Identifier id |
    exists(f.getKind()) and
    v.getAstNode() = TIdentifier(id) and
    (id = f.getVariable() or id = f.getKey() or id = f.getValue()) and
    result = f.getBody()
  )
  or
  exists(UCODE::ForInAltStatement f, UCODE::Identifier id |
    exists(f.getKind()) and
    v.getAstNode() = TIdentifier(id) and
    (id = f.getVariable() or id = f.getKey() or id = f.getValue()) and
    result = f.getBody()
  )
  or
  exists(UCODE::CatchClause c, UCODE::Identifier id |
    v.getAstNode() = TIdentifier(id) and id = c.getParameter() and result = c.getBody()
  )
  or
  exists(UCODE::Identifier id |
    namedFormalIdentifier(id) and
    v.getAstNode() = TIdentifier(id) and
    result = functionBodyOfFormal(id)
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
  exists(UCODE::Identifier ident, UCODE::AstNode scope |
    scope = bindingScope(v) and
    ident.getValue() = name and
    name = v.getName() and
    ident.getParent+() = scope and
    node = TIdentifier(ident) and
    not exists(UCODE::VariableDeclarator d | d.getName() = ident) and
    not exists(UCODE::FormalParameters ps | ident.getParent+() = ps) and
    not exists(UCODE::FunctionDeclaration f | f.getName() = ident) and
    not exists(UCODE::FunctionExpression f | f.getName() = ident) and
    not exists(UCODE::ArrowFunction f | f.getParameter() = ident) and
    not exists(UCODE::CatchClause c | c.getParameter() = ident) and
    not exists(UCODE::ForInStatement f |
      exists(f.getKind()) and
      (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
    ) and
    not exists(UCODE::ForInAltStatement f |
      exists(f.getKind()) and
      (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
    ) and
    not exists(Variable other, UCODE::AstNode inner |
      other != v and
      other.getName() = name and
      inner = bindingScope(other) and
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
  or
  exists(UCODE::ForInStatement f |
    not exists(f.getKind()) and
    (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
  )
  or
  exists(UCODE::ForInAltStatement f |
    not exists(f.getKind()) and
    (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
  )
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

  /** Identifier token of this write. */
  UCODE::Identifier getIdentifier() { this.getAstNode() = TIdentifier(result) }

  /**
   * Assignment, update, or assignment-form `for-in` that writes this
   * identifier. Not a `let`/`const` declarator.
   */
  UCODE::AstNode getWriteOperation() {
    exists(UCODE::Identifier ident | ident = this.getIdentifier() |
      result.(UCODE::AssignmentExpression).getLeft() = ident
      or
      result.(UCODE::AugmentedAssignmentExpression).getLeft() = ident
      or
      result.(UCODE::UpdateExpression).getArgument() = ident
      or
      exists(UCODE::ForInStatement f |
        not exists(f.getKind()) and
        result = f and
        (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
      )
      or
      exists(UCODE::ForInAltStatement f |
        not exists(f.getKind()) and
        result = f and
        (ident = f.getVariable() or ident = f.getKey() or ident = f.getValue())
      )
    )
  }

  /**
   * RHS stored by `=` or by `&&=` / `||=` / `??=`. Arithmetic `+=` and
   * updates have no assigned RHS; those are not value-preserving copies.
   */
  UCODE::AstNode getAssignedRhs() {
    exists(UCODE::AssignmentExpression a |
      a = this.getWriteOperation() and result = a.getRight()
    )
    or
    exists(UCODE::AugmentedAssignmentExpression a |
      a = this.getWriteOperation() and
      a.getOperator() in ["&&=", "||=", "??="] and
      result = a.getRight()
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

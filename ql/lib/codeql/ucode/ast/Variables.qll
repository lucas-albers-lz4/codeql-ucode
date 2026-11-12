/**
 * ucode variables from lexical `let`/`const` declarators.
 *
 * Generator leftover `codeql.bicep` imports, ParameterDeclaration/OutputDeclaration,
 * and `getEnclosingCfgScope` are intentionally absent. Name binding is same-file
 * only; SSA should replace this once dataflow compiles.
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

private predicate access(AstNode node, Variable v, string name) {
  exists(UCODE::Identifier ident |
    ident.getValue() = name and
    name = v.getName() and
    ident.getLocation().getFile() = v.getLocation().getFile() and
    node = TIdentifier(ident) and
    not exists(UCODE::VariableDeclarator d | d.getName() = ident)
  )
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
  VariableWriteAccess() { none() }

  override string getAPrimaryQlClass() { result = "VariableWrite" }
}

class VariableReadAccess extends VariableAccess {
  VariableReadAccess() { not this instanceof VariableWriteAccess }

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

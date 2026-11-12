private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter
private import Expr

/**
 * An identifier expression.
 */
class IdentsImpl extends ExprImpl {
  override string getAPrimaryQlClass() { result = "Identifier" }

  abstract string getName();
}


/**
 * Call Expr
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter
private import Expr
private import Idents

/**
 * Call Expression
 */
class CallsImpl extends AstNode, TCalls {
  override string getAPrimaryQlClass() { result = "CallImpl" }

  abstract IdentsImpl getIdentifier();

  abstract ExprImpl getArguments();

  abstract ExprImpl getArgument(int n);
}

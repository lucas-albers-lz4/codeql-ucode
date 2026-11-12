
/**
 * Loop statements for AST nodes.
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter
private import Expr
private import Idents

/**
 * Loop statements.
 */
abstract class LoopsImpl extends AstNode, TLoops {
  override string getAPrimaryQlClass() { result = "Loops" }

  abstract ExprImpl getCondition();

  abstract ExprImpl getBody();

  abstract IdentsImpl getInitializer();
}
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
 *
 * Mapping overlap puts some loop nodes in StmtsImpl rather than this class.
 * Methods default to none() so those nodes still typecheck.
 */
class LoopsImpl extends AstNode, TLoops {
  override string getAPrimaryQlClass() { result = "Loops" }

  ExprImpl getCondition() { none() }

  ExprImpl getBody() { none() }

  IdentsImpl getInitializer() { none() }
}

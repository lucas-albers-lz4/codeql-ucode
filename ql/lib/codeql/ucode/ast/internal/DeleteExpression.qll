/**
 *  Internal implementation for DeleteExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A DeleteExpression AST Node.
 */
class DeleteExpressionImpl extends TDeleteExpression, ExprImpl {
  private UCODE::DeleteExpression ast;

  override string getAPrimaryQlClass() { result = "DeleteExpression" }

  DeleteExpressionImpl() { this = TDeleteExpression(ast) }

  override string toString() { result = ast.toString() }
}
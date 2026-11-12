/**
 *  Internal implementation for UpdateExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A UpdateExpression AST Node.
 */
class UpdateExpressionImpl extends TUpdateExpression, ExprImpl {
  private UCODE::UpdateExpression ast;

  override string getAPrimaryQlClass() { result = "UpdateExpression" }

  UpdateExpressionImpl() { this = TUpdateExpression(ast) }

  override string toString() { result = ast.toString() }
}
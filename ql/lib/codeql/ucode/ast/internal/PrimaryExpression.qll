/**
 *  Internal implementation for PrimaryExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A PrimaryExpression AST Node.
 */
class PrimaryExpressionImpl extends TPrimaryExpression, ExprImpl {
  private UCODE::PrimaryExpression ast;

  override string getAPrimaryQlClass() { result = "PrimaryExpression" }

  PrimaryExpressionImpl() { this = TPrimaryExpression(ast) }

  override string toString() { result = ast.toString() }
}
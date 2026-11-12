/**
 *  Internal implementation for ParenthesizedExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A ParenthesizedExpression AST Node.
 */
class ParenthesizedExpressionImpl extends TParenthesizedExpression, ExprImpl {
  private UCODE::ParenthesizedExpression ast;

  override string getAPrimaryQlClass() { result = "ParenthesizedExpression" }

  ParenthesizedExpressionImpl() { this = TParenthesizedExpression(ast) }

  override string toString() { result = ast.toString() }
}
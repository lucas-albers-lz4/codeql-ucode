/**
 *  Internal implementation for FunctionExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A FunctionExpression AST Node.
 */
class FunctionExpressionImpl extends TFunctionExpression, ExprImpl {
  private UCODE::FunctionExpression ast;

  override string getAPrimaryQlClass() { result = "FunctionExpression" }

  FunctionExpressionImpl() { this = TFunctionExpression(ast) }

  override string toString() { result = ast.toString() }
}
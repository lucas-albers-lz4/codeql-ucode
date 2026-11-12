/**
 *  Internal implementation for BinaryExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A BinaryExpression AST Node.
 */
class BinaryExpressionImpl extends TBinaryExpression, ExprImpl {
  private UCODE::BinaryExpression ast;

  override string getAPrimaryQlClass() { result = "BinaryExpression" }

  BinaryExpressionImpl() { this = TBinaryExpression(ast) }

  override string toString() { result = ast.toString() }
}
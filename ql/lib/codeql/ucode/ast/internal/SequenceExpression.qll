/**
 *  Internal implementation for SequenceExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A SequenceExpression AST Node.
 */
class SequenceExpressionImpl extends TSequenceExpression, ExprImpl {
  private UCODE::SequenceExpression ast;

  override string getAPrimaryQlClass() { result = "SequenceExpression" }

  SequenceExpressionImpl() { this = TSequenceExpression(ast) }

  override string toString() { result = ast.toString() }
}
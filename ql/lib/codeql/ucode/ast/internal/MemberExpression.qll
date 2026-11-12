/**
 *  Internal implementation for MemberExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A MemberExpression AST Node.
 */
class MemberExpressionImpl extends TMemberExpression, ExprImpl {
  private UCODE::MemberExpression ast;

  override string getAPrimaryQlClass() { result = "MemberExpression" }

  MemberExpressionImpl() { this = TMemberExpression(ast) }

  override string toString() { result = ast.toString() }
}
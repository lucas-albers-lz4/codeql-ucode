/**
 *  Internal implementation for AugmentedAssignmentExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Expr

/**
 *  A AugmentedAssignmentExpression AST Node.
 */
class AugmentedAssignmentExpressionImpl extends TAugmentedAssignmentExpression, ExprImpl {
  private UCODE::AugmentedAssignmentExpression ast;

  override string getAPrimaryQlClass() { result = "AugmentedAssignmentExpression" }

  AugmentedAssignmentExpressionImpl() { this = TAugmentedAssignmentExpression(ast) }

  override string toString() { result = ast.toString() }
}
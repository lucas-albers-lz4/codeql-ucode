/**
 *  Internal implementation for CallExpression
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Calls
private import Idents
private import Expr

/**
 *  A CallExpression AST Node.
 */
class CallExpressionImpl extends TCallExpression, CallsImpl {
  private UCODE::CallExpression ast;

  override string getAPrimaryQlClass() { result = "CallExpression" }

  CallExpressionImpl() { this = TCallExpression(ast) }

  override string toString() { result = ast.toString() }
  override IdentsImpl getIdentifier() { none() }

  override ExprImpl getArguments() { none() }

  /**
   * Gets the `n`th extracted argument expression.
   *
   * Children that are not `TExpr` (template strings, numbers, arrays,
   * objects, spreads, arrows, `this`) have no result. `getArguments()`
   * stays `none()` because the `arguments` node is not an expression.
   */
  override ExprImpl getArgument(int n) {
    toTreeSitter(result) = ast.getArguments().getChild(n)
  }
}
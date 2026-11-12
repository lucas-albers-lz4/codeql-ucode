/**
 *  Internal implementation for SwitchBody
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A SwitchBody AST Node.
 */
class SwitchBodyImpl extends TSwitchBody, ConditionalsImpl {
  private UCODE::SwitchBody ast;

  override string getAPrimaryQlClass() { result = "SwitchBody" }

  SwitchBodyImpl() { this = TSwitchBody(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
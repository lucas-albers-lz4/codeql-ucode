/**
 *  Internal implementation for SwitchDefault
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A SwitchDefault AST Node.
 */
class SwitchDefaultImpl extends TSwitchDefault, ConditionalsImpl {
  private UCODE::SwitchDefault ast;

  override string getAPrimaryQlClass() { result = "SwitchDefault" }

  SwitchDefaultImpl() { this = TSwitchDefault(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
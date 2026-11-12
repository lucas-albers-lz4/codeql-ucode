/**
 *  Internal implementation for SwitchCase
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A SwitchCase AST Node.
 */
class SwitchCaseImpl extends TSwitchCase, ConditionalsImpl {
  private UCODE::SwitchCase ast;

  override string getAPrimaryQlClass() { result = "SwitchCase" }

  SwitchCaseImpl() { this = TSwitchCase(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
/**
 *  Internal implementation for Default
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A Default AST Node.
 */
class DefaultImpl extends TDefault, ConditionalsImpl {
  private UCODE::Default ast;

  override string getAPrimaryQlClass() { result = "Default" }

  DefaultImpl() { this = TDefault(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
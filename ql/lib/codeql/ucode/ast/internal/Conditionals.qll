
/**
 * Conditional statements.
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter
private import Expr

/**
 * Conditional statements.
 */
class ConditionalsImpl extends ExprImpl, TConditionals {
  override string getAPrimaryQlClass() { result = "Conditional" }

  abstract ExprImpl getCondition();
}
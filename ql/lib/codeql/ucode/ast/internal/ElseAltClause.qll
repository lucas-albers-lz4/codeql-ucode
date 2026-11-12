/**
 *  Internal implementation for ElseAltClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A ElseAltClause AST Node.
 */
class ElseAltClauseImpl extends TElseAltClause, ConditionalsImpl {
  private UCODE::ElseAltClause ast;

  override string getAPrimaryQlClass() { result = "ElseAltClause" }

  ElseAltClauseImpl() { this = TElseAltClause(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
/**
 *  Internal implementation for ElseClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Conditionals
private import Expr

/**
 *  A ElseClause AST Node.
 */
class ElseClauseImpl extends TElseClause, ConditionalsImpl {
  private UCODE::ElseClause ast;

  override string getAPrimaryQlClass() { result = "ElseClause" }

  ElseClauseImpl() { this = TElseClause(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override ExprImpl getCondition() {
    none()
  }
}
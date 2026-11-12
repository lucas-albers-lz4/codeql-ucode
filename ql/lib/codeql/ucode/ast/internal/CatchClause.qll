/**
 *  Internal implementation for CatchClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A CatchClause AST Node.
 */
class CatchClauseImpl extends TCatchClause, AstNode {
  private UCODE::CatchClause ast;

  override string getAPrimaryQlClass() { result = "CatchClause" }

  CatchClauseImpl() { this = TCatchClause(ast) }

  override string toString() { result = ast.toString() }
}
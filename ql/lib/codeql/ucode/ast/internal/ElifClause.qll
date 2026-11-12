/**
 *  Internal implementation for ElifClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ElifClause AST Node.
 */
class ElifClauseImpl extends TElifClause, AstNode {
  private UCODE::ElifClause ast;

  override string getAPrimaryQlClass() { result = "ElifClause" }

  ElifClauseImpl() { this = TElifClause(ast) }

  override string toString() { result = ast.toString() }
}
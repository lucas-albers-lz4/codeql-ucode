/**
 *  Internal implementation for StatementList
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A StatementList AST Node.
 */
class StatementListImpl extends TStatementList, StmtsImpl {
  private UCODE::StatementList ast;

  override string getAPrimaryQlClass() { result = "StatementList" }

  StatementListImpl() { this = TStatementList(ast) }

  override string toString() { result = ast.toString() }
}
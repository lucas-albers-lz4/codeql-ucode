/**
 *  Internal implementation for StatementBlock
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A StatementBlock AST Node.
 */
class StatementBlockImpl extends TStatementBlock, StmtsImpl {
  private UCODE::StatementBlock ast;

  override string getAPrimaryQlClass() { result = "StatementBlock" }

  StatementBlockImpl() { this = TStatementBlock(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for TryStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A TryStatement AST Node.
 */
class TryStatementImpl extends TTryStatement, StmtsImpl {
  private UCODE::TryStatement ast;

  override string getAPrimaryQlClass() { result = "TryStatement" }

  TryStatementImpl() { this = TTryStatement(ast) }

  override string toString() { result = ast.toString() }
}
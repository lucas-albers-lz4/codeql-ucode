/**
 *  Internal implementation for ContinueStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ContinueStatement AST Node.
 */
class ContinueStatementImpl extends TContinueStatement, StmtsImpl {
  private UCODE::ContinueStatement ast;

  override string getAPrimaryQlClass() { result = "ContinueStatement" }

  ContinueStatementImpl() { this = TContinueStatement(ast) }

  override string toString() { result = ast.toString() }
}
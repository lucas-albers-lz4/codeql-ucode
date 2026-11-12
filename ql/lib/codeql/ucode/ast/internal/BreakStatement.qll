/**
 *  Internal implementation for BreakStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A BreakStatement AST Node.
 */
class BreakStatementImpl extends TBreakStatement, StmtsImpl {
  private UCODE::BreakStatement ast;

  override string getAPrimaryQlClass() { result = "BreakStatement" }

  BreakStatementImpl() { this = TBreakStatement(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for EmptyStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A EmptyStatement AST Node.
 */
class EmptyStatementImpl extends TEmptyStatement, StmtsImpl {
  private UCODE::EmptyStatement ast;

  override string getAPrimaryQlClass() { result = "EmptyStatement" }

  EmptyStatementImpl() { this = TEmptyStatement(ast) }

  override string toString() { result = ast.toString() }
}
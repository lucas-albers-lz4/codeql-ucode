/**
 *  Internal implementation for ExpressionStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ExpressionStatement AST Node.
 */
class ExpressionStatementImpl extends TExpressionStatement, StmtsImpl {
  private UCODE::ExpressionStatement ast;

  override string getAPrimaryQlClass() { result = "ExpressionStatement" }

  ExpressionStatementImpl() { this = TExpressionStatement(ast) }

  override string toString() { result = ast.toString() }
}
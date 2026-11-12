/**
 *  Internal implementation for ReturnStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ReturnStatement AST Node.
 */
class ReturnStatementImpl extends TReturnStatement, StmtsImpl {
  private UCODE::ReturnStatement ast;

  override string getAPrimaryQlClass() { result = "ReturnStatement" }

  ReturnStatementImpl() { this = TReturnStatement(ast) }

  override string toString() { result = ast.toString() }
}
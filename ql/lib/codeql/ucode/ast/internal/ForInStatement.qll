/**
 *  Internal implementation for ForInStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ForInStatement AST Node.
 */
class ForInStatementImpl extends TForInStatement, StmtsImpl {
  private UCODE::ForInStatement ast;

  override string getAPrimaryQlClass() { result = "ForInStatement" }

  ForInStatementImpl() { this = TForInStatement(ast) }

  override string toString() { result = ast.toString() }
}
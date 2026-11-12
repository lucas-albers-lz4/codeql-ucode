/**
 *  Internal implementation for ForAltStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ForAltStatement AST Node.
 */
class ForAltStatementImpl extends TForAltStatement, StmtsImpl {
  private UCODE::ForAltStatement ast;

  override string getAPrimaryQlClass() { result = "ForAltStatement" }

  ForAltStatementImpl() { this = TForAltStatement(ast) }

  override string toString() { result = ast.toString() }
}
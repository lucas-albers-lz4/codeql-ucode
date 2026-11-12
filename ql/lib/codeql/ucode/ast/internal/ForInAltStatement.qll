/**
 *  Internal implementation for ForInAltStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ForInAltStatement AST Node.
 */
class ForInAltStatementImpl extends TForInAltStatement, StmtsImpl {
  private UCODE::ForInAltStatement ast;

  override string getAPrimaryQlClass() { result = "ForInAltStatement" }

  ForInAltStatementImpl() { this = TForInAltStatement(ast) }

  override string toString() { result = ast.toString() }
}
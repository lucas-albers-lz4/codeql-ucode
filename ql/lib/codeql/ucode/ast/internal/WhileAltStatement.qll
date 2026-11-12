/**
 *  Internal implementation for WhileAltStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A WhileAltStatement AST Node.
 */
class WhileAltStatementImpl extends TWhileAltStatement, StmtsImpl {
  private UCODE::WhileAltStatement ast;

  override string getAPrimaryQlClass() { result = "WhileAltStatement" }

  WhileAltStatementImpl() { this = TWhileAltStatement(ast) }

  override string toString() { result = ast.toString() }
}
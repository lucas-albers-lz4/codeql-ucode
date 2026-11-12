/**
 *  Internal implementation for WhileStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A WhileStatement AST Node.
 */
class WhileStatementImpl extends TWhileStatement, StmtsImpl {
  private UCODE::WhileStatement ast;

  override string getAPrimaryQlClass() { result = "WhileStatement" }

  WhileStatementImpl() { this = TWhileStatement(ast) }

  override string toString() { result = ast.toString() }
}
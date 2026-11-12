/**
 *  Internal implementation for IfStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A IfStatement AST Node.
 */
class IfStatementImpl extends TIfStatement, StmtsImpl {
  private UCODE::IfStatement ast;

  override string getAPrimaryQlClass() { result = "IfStatement" }

  IfStatementImpl() { this = TIfStatement(ast) }

  override string toString() { result = ast.toString() }
}
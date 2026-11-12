/**
 *  Internal implementation for SwitchStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A SwitchStatement AST Node.
 */
class SwitchStatementImpl extends TSwitchStatement, StmtsImpl {
  private UCODE::SwitchStatement ast;

  override string getAPrimaryQlClass() { result = "SwitchStatement" }

  SwitchStatementImpl() { this = TSwitchStatement(ast) }

  override string toString() { result = ast.toString() }
}
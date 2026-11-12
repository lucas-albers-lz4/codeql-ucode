/**
 *  Internal implementation for IfAltStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A IfAltStatement AST Node.
 */
class IfAltStatementImpl extends TIfAltStatement, StmtsImpl {
  private UCODE::IfAltStatement ast;

  override string getAPrimaryQlClass() { result = "IfAltStatement" }

  IfAltStatementImpl() { this = TIfAltStatement(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for ExportStatement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A ExportStatement AST Node.
 */
class ExportStatementImpl extends TExportStatement, StmtsImpl {
  private UCODE::ExportStatement ast;

  override string getAPrimaryQlClass() { result = "ExportStatement" }

  ExportStatementImpl() { this = TExportStatement(ast) }

  override string toString() { result = ast.toString() }
}
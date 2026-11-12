/**
 *  Internal implementation for ExportClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A ExportClause AST Node.
 */
class ExportClauseImpl extends TExportClause, AstNode {
  private UCODE::ExportClause ast;

  override string getAPrimaryQlClass() { result = "ExportClause" }

  ExportClauseImpl() { this = TExportClause(ast) }

  override string toString() { result = ast.toString() }
}
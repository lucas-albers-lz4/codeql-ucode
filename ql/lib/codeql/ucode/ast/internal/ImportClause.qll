/**
 *  Internal implementation for ImportClause
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ImportClause AST Node.
 */
class ImportClauseImpl extends TImportClause, AstNode {
  private UCODE::ImportClause ast;

  override string getAPrimaryQlClass() { result = "ImportClause" }

  ImportClauseImpl() { this = TImportClause(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for ExportSpecifier
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A ExportSpecifier AST Node.
 */
class ExportSpecifierImpl extends TExportSpecifier, AstNode {
  private UCODE::ExportSpecifier ast;

  override string getAPrimaryQlClass() { result = "ExportSpecifier" }

  ExportSpecifierImpl() { this = TExportSpecifier(ast) }

  override string toString() { result = ast.toString() }
}
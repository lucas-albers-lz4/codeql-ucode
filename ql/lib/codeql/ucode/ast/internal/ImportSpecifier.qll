/**
 *  Internal implementation for ImportSpecifier
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ImportSpecifier AST Node.
 */
class ImportSpecifierImpl extends TImportSpecifier, AstNode {
  private UCODE::ImportSpecifier ast;

  override string getAPrimaryQlClass() { result = "ImportSpecifier" }

  ImportSpecifierImpl() { this = TImportSpecifier(ast) }

  override string toString() { result = ast.toString() }
}
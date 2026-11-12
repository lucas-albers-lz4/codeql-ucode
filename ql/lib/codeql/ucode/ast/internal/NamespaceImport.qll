/**
 *  Internal implementation for NamespaceImport
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A NamespaceImport AST Node.
 */
class NamespaceImportImpl extends TNamespaceImport, AstNode {
  private UCODE::NamespaceImport ast;

  override string getAPrimaryQlClass() { result = "NamespaceImport" }

  NamespaceImportImpl() { this = TNamespaceImport(ast) }

  override string toString() { result = ast.toString() }
}
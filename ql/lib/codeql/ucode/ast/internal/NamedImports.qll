/**
 *  Internal implementation for NamedImports
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A NamedImports AST Node.
 */
class NamedImportsImpl extends TNamedImports, AstNode {
  private UCODE::NamedImports ast;

  override string getAPrimaryQlClass() { result = "NamedImports" }

  NamedImportsImpl() { this = TNamedImports(ast) }

  override string toString() { result = ast.toString() }
}
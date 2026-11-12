/**
 *  Internal implementation for RestElement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A RestElement AST Node.
 */
class RestElementImpl extends TRestElement, AstNode {
  private UCODE::RestElement ast;

  override string getAPrimaryQlClass() { result = "RestElement" }

  RestElementImpl() { this = TRestElement(ast) }

  override string toString() { result = ast.toString() }
}
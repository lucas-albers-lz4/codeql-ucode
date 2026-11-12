/**
 *  Internal implementation for SpreadElement
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A SpreadElement AST Node.
 */
class SpreadElementImpl extends TSpreadElement, AstNode {
  private UCODE::SpreadElement ast;

  override string getAPrimaryQlClass() { result = "SpreadElement" }

  SpreadElementImpl() { this = TSpreadElement(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for PropertyIdentifier
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Idents

/**
 *  A PropertyIdentifier AST Node.
 */
class PropertyIdentifierImpl extends TPropertyIdentifier, IdentsImpl {
  private UCODE::PropertyIdentifier ast;

  override string getAPrimaryQlClass() { result = "PropertyIdentifier" }

  PropertyIdentifierImpl() { this = TPropertyIdentifier(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override string getName() { result = ast.getValue() }
}
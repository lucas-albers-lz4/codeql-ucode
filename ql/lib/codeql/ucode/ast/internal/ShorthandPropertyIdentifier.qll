/**
 *  Internal implementation for ShorthandPropertyIdentifier
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Idents

/**
 *  A ShorthandPropertyIdentifier AST Node.
 */
class ShorthandPropertyIdentifierImpl extends TShorthandPropertyIdentifier, IdentsImpl {
  private UCODE::ShorthandPropertyIdentifier ast;

  override string getAPrimaryQlClass() { result = "ShorthandPropertyIdentifier" }

  ShorthandPropertyIdentifierImpl() { this = TShorthandPropertyIdentifier(ast) }

  override string toString() { result = ast.toString() }
  /**
   * Get the condition
   */
  override string getName() { result = ast.getValue() }
}
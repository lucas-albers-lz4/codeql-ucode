/**
 *  Internal implementation for This
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A This AST Node.
 */
class ThisImpl extends TThis, AstNode {
  private UCODE::This ast;

  override string getAPrimaryQlClass() { result = "This" }

  ThisImpl() { this = TThis(ast) }

  override string toString() { result = ast.toString() }
}
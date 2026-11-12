/**
 *  Internal implementation for Null
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import LiteralAbstracts

/**
 *  A Null AST Node.
 */
class NullImpl extends TNull, LiteralAbstractsImpl {
  private UCODE::Null ast;

  override string getAPrimaryQlClass() { result = "Null" }

  NullImpl() { this = TNull(ast) }

  override string toString() { result = ast.toString() }
}
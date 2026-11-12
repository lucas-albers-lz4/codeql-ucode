/**
 *  Internal implementation for Null
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Literals

/**
 *  A Null AST Node.
 */
class NullImpl extends TNull, LiteralsImpl {
  private UCODE::Null ast;

  override string getAPrimaryQlClass() { result = "Null" }

  NullImpl() { this = TNull(ast) }

  override string toString() { result = ast.toString() }

  override string getValue() { result = ast.getValue() }
}

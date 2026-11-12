/**
 *  Internal implementation for True
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Literals

/**
 *  A True AST Node.
 */
class TrueImpl extends TTrue, LiteralsImpl {
  private UCODE::True ast;

  override string getAPrimaryQlClass() { result = "True" }

  TrueImpl() { this = TTrue(ast) }

  override string toString() { result = ast.toString() }
  /**
   *  Get the literal value
   */
  override string getValue() { result = ast.getValue() }
}
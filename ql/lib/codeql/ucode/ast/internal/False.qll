/**
 *  Internal implementation for False
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Literals

/**
 *  A False AST Node.
 */
class FalseImpl extends TFalse, LiteralsImpl {
  private UCODE::False ast;

  override string getAPrimaryQlClass() { result = "False" }

  FalseImpl() { this = TFalse(ast) }

  override string toString() { result = ast.toString() }
  /**
   *  Get the literal value
   */
  override string getValue() { result = ast.getValue() }
}
/**
 *  Internal implementation for Array
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A Array AST Node.
 */
class ArrayImpl extends TArray, AstNode {
  private UCODE::Array ast;

  override string getAPrimaryQlClass() { result = "Array" }

  ArrayImpl() { this = TArray(ast) }

  override string toString() { result = ast.toString() }
}
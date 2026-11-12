/**
 *  Internal implementation for ArrowFunction
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ArrowFunction AST Node.
 */
class ArrowFunctionImpl extends TArrowFunction, AstNode {
  private UCODE::ArrowFunction ast;

  override string getAPrimaryQlClass() { result = "ArrowFunction" }

  ArrowFunctionImpl() { this = TArrowFunction(ast) }

  override string toString() { result = ast.toString() }
}
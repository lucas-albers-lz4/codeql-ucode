/**
 *  Internal implementation for ComputedPropertyName
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ComputedPropertyName AST Node.
 */
class ComputedPropertyNameImpl extends TComputedPropertyName, AstNode {
  private UCODE::ComputedPropertyName ast;

  override string getAPrimaryQlClass() { result = "ComputedPropertyName" }

  ComputedPropertyNameImpl() { this = TComputedPropertyName(ast) }

  override string toString() { result = ast.toString() }
}
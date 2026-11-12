/**
 *  Internal implementation for VariableDeclarator
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A VariableDeclarator AST Node.
 */
class VariableDeclaratorImpl extends TVariableDeclarator, AstNode {
  private UCODE::VariableDeclarator ast;

  override string getAPrimaryQlClass() { result = "VariableDeclarator" }

  VariableDeclaratorImpl() { this = TVariableDeclarator(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for Arguments
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A Arguments AST Node.
 */
class ArgumentsImpl extends TArguments, AstNode {
  private UCODE::Arguments ast;

  override string getAPrimaryQlClass() { result = "Arguments" }

  ArgumentsImpl() { this = TArguments(ast) }

  override string toString() { result = ast.toString() }
}
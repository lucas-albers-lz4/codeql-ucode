/**
 *  Internal implementation for Regex
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A Regex AST Node.
 */
class RegexImpl extends TRegex, AstNode {
  private UCODE::Regex ast;

  override string getAPrimaryQlClass() { result = "Regex" }

  RegexImpl() { this = TRegex(ast) }

  override string toString() { result = ast.toString() }
}
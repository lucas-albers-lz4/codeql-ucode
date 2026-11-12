/**
 *  Internal implementation for RegexPattern
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A RegexPattern AST Node.
 */
class RegexPatternImpl extends TRegexPattern, AstNode {
  private UCODE::RegexPattern ast;

  override string getAPrimaryQlClass() { result = "RegexPattern" }

  RegexPatternImpl() { this = TRegexPattern(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for RegexFlags
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A RegexFlags AST Node.
 */
class RegexFlagsImpl extends TRegexFlags, AstNode {
  private UCODE::RegexFlags ast;

  override string getAPrimaryQlClass() { result = "RegexFlags" }

  RegexFlagsImpl() { this = TRegexFlags(ast) }

  override string toString() { result = ast.toString() }
}
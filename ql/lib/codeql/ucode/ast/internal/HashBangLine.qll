/**
 *  Internal implementation for HashBangLine
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A HashBangLine AST Node.
 */
class HashBangLineImpl extends THashBangLine, AstNode {
  private UCODE::HashBangLine ast;

  override string getAPrimaryQlClass() { result = "HashBangLine" }

  HashBangLineImpl() { this = THashBangLine(ast) }

  override string toString() { result = ast.toString() }
}
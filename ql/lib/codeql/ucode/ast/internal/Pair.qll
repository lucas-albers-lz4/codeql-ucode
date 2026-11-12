/**
 *  Internal implementation for Pair
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A Pair AST Node.
 */
class PairImpl extends TPair, AstNode {
  private UCODE::Pair ast;

  override string getAPrimaryQlClass() { result = "Pair" }

  PairImpl() { this = TPair(ast) }

  override string toString() { result = ast.toString() }
}
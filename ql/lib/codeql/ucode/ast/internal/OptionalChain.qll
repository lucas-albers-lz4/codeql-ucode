/**
 *  Internal implementation for OptionalChain
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A OptionalChain AST Node.
 */
class OptionalChainImpl extends TOptionalChain, AstNode {
  private UCODE::OptionalChain ast;

  override string getAPrimaryQlClass() { result = "OptionalChain" }

  OptionalChainImpl() { this = TOptionalChain(ast) }

  override string toString() { result = ast.toString() }
}
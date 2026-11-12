/**
 *  Internal implementation for ReservedWord
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A ReservedWord AST Node.
 */
class ReservedWordImpl extends TReservedWord, AstNode {
  private UCODE::ReservedWord ast;

  override string getAPrimaryQlClass() { result = "ReservedWord" }

  ReservedWordImpl() { this = TReservedWord(ast) }

  override string toString() { result = ast.toString() }
}
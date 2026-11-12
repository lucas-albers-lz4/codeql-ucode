/**
 *  Internal implementation for LexicalDeclaration
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A LexicalDeclaration AST Node.
 */
class LexicalDeclarationImpl extends TLexicalDeclaration, StmtsImpl {
  private UCODE::LexicalDeclaration ast;

  override string getAPrimaryQlClass() { result = "LexicalDeclaration" }

  LexicalDeclarationImpl() { this = TLexicalDeclaration(ast) }

  override string toString() { result = ast.toString() }
}
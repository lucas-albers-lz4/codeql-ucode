/**
 *  Internal implementation for String
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import LiteralAbstracts

/**
 *  A String AST Node.
 */
class StringImpl extends TString, LiteralAbstractsImpl {
  private UCODE::String ast;

  override string getAPrimaryQlClass() { result = "String" }

  StringImpl() { this = TString(ast) }

  override string toString() { result = ast.toString() }
}
/**
 *  Internal implementation for String
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Literals

/**
 *  A String AST Node.
 */
class StringImpl extends TString, LiteralsImpl {
  private UCODE::String ast;

  override string getAPrimaryQlClass() { result = "String" }

  StringImpl() { this = TString(ast) }

  override string toString() { result = ast.toString() }

  override string getValue() {
    result =
      concat(int i, UCODE::AstNode n |
        n = ast.getChild(i)
      |
        n.(UCODE::Token).getValue() order by i
      )
  }
}

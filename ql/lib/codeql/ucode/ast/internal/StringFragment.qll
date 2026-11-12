/**
 *  Internal implementation for StringFragment
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Literals

/**
 *  A StringFragment AST Node.
 */
class StringFragmentImpl extends TStringFragment, LiteralsImpl {
  private UCODE::StringFragment ast;

  override string getAPrimaryQlClass() { result = "StringFragment" }

  StringFragmentImpl() { this = TStringFragment(ast) }

  override string toString() { result = ast.toString() }

  override string getValue() { result = ast.getValue() }
}

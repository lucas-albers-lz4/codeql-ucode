/**
 *  Internal implementation for Object
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter

/**
 *  A Object AST Node.
 */
class ObjectImpl extends TObject, AstNode {
  private UCODE::Object ast;

  override string getAPrimaryQlClass() { result = "Object" }

  ObjectImpl() { this = TObject(ast) }

  override string toString() { result = ast.toString() }
}
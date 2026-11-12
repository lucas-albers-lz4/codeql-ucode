/**
 *  Internal implementation for TemplateString
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A TemplateString AST Node.
 */
class TemplateStringImpl extends TTemplateString, AstNode {
  private UCODE::TemplateString ast;

  override string getAPrimaryQlClass() { result = "TemplateString" }

  TemplateStringImpl() { this = TTemplateString(ast) }

  override string toString() { result = ast.toString() }
}
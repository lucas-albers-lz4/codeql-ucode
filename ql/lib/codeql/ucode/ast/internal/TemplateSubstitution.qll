/**
 *  Internal implementation for TemplateSubstitution
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter

/**
 *  A TemplateSubstitution AST Node.
 */
class TemplateSubstitutionImpl extends TTemplateSubstitution, AstNode {
  private UCODE::TemplateSubstitution ast;

  override string getAPrimaryQlClass() { result = "TemplateSubstitution" }

  TemplateSubstitutionImpl() { this = TTemplateSubstitution(ast) }

  override string toString() { result = ast.toString() }
}
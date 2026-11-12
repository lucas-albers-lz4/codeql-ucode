/**
 *  Internal implementation for FunctionDeclaration
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A FunctionDeclaration AST Node.
 */
class FunctionDeclarationImpl extends TFunctionDeclaration, StmtsImpl {
  private UCODE::FunctionDeclaration ast;

  override string getAPrimaryQlClass() { result = "FunctionDeclaration" }

  FunctionDeclarationImpl() { this = TFunctionDeclaration(ast) }

  override string toString() { result = ast.toString() }
}
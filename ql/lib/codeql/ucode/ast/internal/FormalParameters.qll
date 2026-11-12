/**
 *  Internal implementation for FormalParameters
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Loops
private import Idents
private import Expr

/**
 *  A FormalParameters AST Node.
 */
class FormalParametersImpl extends TFormalParameters, LoopsImpl {
  private UCODE::FormalParameters ast;

  override string getAPrimaryQlClass() { result = "FormalParameters" }

  FormalParametersImpl() { this = TFormalParameters(ast) }

  override string toString() { result = ast.toString() }
  override ExprImpl getCondition() { none() }

  override ExprImpl getBody() { none() }

  override IdentsImpl getInitializer() { none() }
}
/**
 *  Internal implementation for DocComment
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import Loops
private import Idents
private import Expr

/**
 *  A DocComment AST Node.
 */
class DocCommentImpl extends TDocComment, LoopsImpl {
  private UCODE::DocComment ast;

  override string getAPrimaryQlClass() { result = "DocComment" }

  DocCommentImpl() { this = TDocComment(ast) }

  override string toString() { result = ast.toString() }
  override ExprImpl getCondition() { none() }

  override ExprImpl getBody() { none() }

  override IdentsImpl getInitializer() { none() }
}
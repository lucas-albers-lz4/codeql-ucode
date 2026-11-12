
/**
 * Loop statements for AST nodes.
 */
private import AstNodes
private import Stmts
private import Expr
private import Idents
// Internal imports
private import internal.Loops
private import internal.DocComment
private import internal.ForAltStatement
private import internal.ForInAltStatement
private import internal.ForInStatement
private import internal.ForStatement
private import internal.FormalParameters
private import internal.WhileAltStatement
private import internal.WhileStatement

/**
 * Loop statements implementation.
 */
class Loops extends Stmts instanceof LoopsImpl {
  /**
   *  Get the condition of the loop.
   */
  abstract Expr getCondition();

  /**
   *  Get the body of the loop.
   */
  abstract Stmts getBody();

  /**
   *  Get the initializer of the loop, if any.
   */
  abstract Idents getInitializer();
}

/**
 *  A DocComment statement.
 */
final class DocComment extends Loops instanceof DocCommentImpl { 
  override Expr getCondition() { result = DocCommentImpl.super.getCondition() }

  override Stmts getBody() { result = DocCommentImpl.super.getBody() }

  override Idents getInitializer() { result = DocCommentImpl.super.getInitializer() }
}

/**
 *  A ForAltStatement statement.
 */
final class ForAltStatement extends Loops instanceof ForAltStatementImpl { 
  override Expr getCondition() { result = ForAltStatementImpl.super.getCondition() }

  override Stmts getBody() { result = ForAltStatementImpl.super.getBody() }

  override Idents getInitializer() { result = ForAltStatementImpl.super.getInitializer() }
}

/**
 *  A ForInAltStatement statement.
 */
final class ForInAltStatement extends Loops instanceof ForInAltStatementImpl { 
  override Expr getCondition() { result = ForInAltStatementImpl.super.getCondition() }

  override Stmts getBody() { result = ForInAltStatementImpl.super.getBody() }

  override Idents getInitializer() { result = ForInAltStatementImpl.super.getInitializer() }
}

/**
 *  A ForInStatement statement.
 */
final class ForInStatement extends Loops instanceof ForInStatementImpl { 
  override Expr getCondition() { result = ForInStatementImpl.super.getCondition() }

  override Stmts getBody() { result = ForInStatementImpl.super.getBody() }

  override Idents getInitializer() { result = ForInStatementImpl.super.getInitializer() }
}

/**
 *  A ForStatement statement.
 */
final class ForStatement extends Loops instanceof ForStatementImpl { 
  override Expr getCondition() { result = ForStatementImpl.super.getCondition() }

  override Stmts getBody() { result = ForStatementImpl.super.getBody() }

  override Idents getInitializer() { result = ForStatementImpl.super.getInitializer() }
}

/**
 *  A FormalParameters statement.
 */
final class FormalParameters extends Loops instanceof FormalParametersImpl { 
  override Expr getCondition() { result = FormalParametersImpl.super.getCondition() }

  override Stmts getBody() { result = FormalParametersImpl.super.getBody() }

  override Idents getInitializer() { result = FormalParametersImpl.super.getInitializer() }
}

/**
 *  A WhileAltStatement statement.
 */
final class WhileAltStatement extends Loops instanceof WhileAltStatementImpl { 
  override Expr getCondition() { result = WhileAltStatementImpl.super.getCondition() }

  override Stmts getBody() { result = WhileAltStatementImpl.super.getBody() }

  override Idents getInitializer() { result = WhileAltStatementImpl.super.getInitializer() }
}

/**
 *  A WhileStatement statement.
 */
final class WhileStatement extends Loops instanceof WhileStatementImpl { 
  override Expr getCondition() { result = WhileStatementImpl.super.getCondition() }

  override Stmts getBody() { result = WhileStatementImpl.super.getBody() }

  override Idents getInitializer() { result = WhileStatementImpl.super.getInitializer() }
}


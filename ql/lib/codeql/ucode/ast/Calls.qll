
/**
 * Calls nodes in the AST.
 */
private import AstNodes
private import Expr
private import Idents
private import Misc
private import Stmts
// Internal imports
private import internal.Calls
private import internal.CallExpression

/**
 * Represents a callable expression in the AST, such as a function or method call.
 * Provides access to the identifier and name of the call expression.
 */
abstract class Callable extends CallsImpl {
  /**
   * Gets the name of the call expression.
   *
   * @return The name as a string.
   */
  string getName() { result = this.getIdentifier().getName() }

  /**
   * Checks if the call expression has a specific name.
   */
  predicate hasName(string name) { this.getName() = name }
}

/**
 * An abstract class representing callable definitions, such as functions
 * and arrow functions.
 */
abstract class CallDefinition instanceof Stmts {
  /**
   * Gets a string representation of this call definition.
   */
  string toString() { result = "CallDef" }

  /**
   * Gets the parameters collection node of this call definition.
   */
  abstract Expr getParameters();

  /**
   * Gets the parameter at the specified index (0-based).
   */
  abstract Expr getParameter(int index);

  /**
   * Gets the body of this call definition.
   */
  abstract StmtSequence getBody();

  Stmts getStmt(int index) {
    result = this.getBody().getStmt(index)
  }
}

/**
 *  Call functions
 */
class Call instanceof Callable {
  Call() { this instanceof CallExpression }

  Idents getIdentifier() {
    result = Callable.super.getIdentifier()
  }

  Expr getArguments() {
    result = Callable.super.getArguments()
  }

  Expr getArgument(int index) {
    result = Callable.super.getArgument(index)
  }

  string toString() { result = "Call[" + super.getName() + "]" }
}


/**
 * A CallExpression expression in the AST.
 */
class CallExpression extends Callable instanceof CallExpressionImpl {
  override Idents getIdentifier() { none() }

  override Expr getArguments() { none() }

  override Expr getArgument(int n) {
    result = CallExpressionImpl.super.getArgument(n)
  }
}
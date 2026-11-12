private import AstNodes
private import internal.AstNodes
private import internal.TreeSitter
private import internal.Expr

private import internal.AssignmentExpression
private import internal.AugmentedAssignmentExpression
private import internal.BinaryExpression
private import internal.CallExpression
private import internal.DeleteExpression
private import internal.Expression
private import internal.ExpressionStatement
private import internal.FunctionExpression
private import internal.MemberExpression
private import internal.ParenthesizedExpression
private import internal.PrimaryExpression
private import internal.SequenceExpression
private import internal.SubscriptExpression
private import internal.TernaryExpression
private import internal.UnaryExpression
private import internal.UpdateExpression

/**
 * An expression in the AST.
 */
final class Expr extends AstNode instanceof ExprImpl { }

/**
 * A AssignmentExpression expression in the AST.
 */
final class AssignmentExpression extends Expr instanceof AssignmentExpressionImpl { }
/**
 * A AugmentedAssignmentExpression expression in the AST.
 */
final class AugmentedAssignmentExpression extends Expr instanceof AugmentedAssignmentExpressionImpl { }
/**
 * A BinaryExpression expression in the AST.
 */
final class BinaryExpression extends Expr instanceof BinaryExpressionImpl { }
/**
 * A DeleteExpression expression in the AST.
 */
final class DeleteExpression extends Expr instanceof DeleteExpressionImpl { }
/**
 * A Expression expression in the AST.
 */
final class Expression extends Expr instanceof ExpressionImpl { }
/**
 * A FunctionExpression expression in the AST.
 */
final class FunctionExpression extends Expr instanceof FunctionExpressionImpl { }
/**
 * A MemberExpression expression in the AST.
 */
final class MemberExpression extends Expr instanceof MemberExpressionImpl { }
/**
 * A ParenthesizedExpression expression in the AST.
 */
final class ParenthesizedExpression extends Expr instanceof ParenthesizedExpressionImpl { }
/**
 * A PrimaryExpression expression in the AST.
 */
final class PrimaryExpression extends Expr instanceof PrimaryExpressionImpl { }
/**
 * A SequenceExpression expression in the AST.
 */
final class SequenceExpression extends Expr instanceof SequenceExpressionImpl { }
/**
 * A SubscriptExpression expression in the AST.
 */
final class SubscriptExpression extends Expr instanceof SubscriptExpressionImpl { }
/**
 * A TernaryExpression expression in the AST.
 */
final class TernaryExpression extends Expr instanceof TernaryExpressionImpl { }
/**
 * A UnaryExpression expression in the AST.
 */
final class UnaryExpression extends Expr instanceof UnaryExpressionImpl { }
/**
 * A UpdateExpression expression in the AST.
 */
final class UpdateExpression extends Expr instanceof UpdateExpressionImpl { }
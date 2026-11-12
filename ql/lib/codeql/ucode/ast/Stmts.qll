/**
 * Statement nodes in the AST.
 */
private import AstNodes
private import internal.AstNodes
private import internal.TreeSitter
private import internal.Stmts
private import internal.StmtSequence
// Sequence Statements
private import internal.Program
private import internal.StatementBlock
// Statements (loop types live in Loops.qll; StatementBlock is StmtSequence only)
private import internal.BreakStatement
private import internal.ContinueStatement
private import internal.Declaration
private import internal.EmptyStatement
private import internal.ExportStatement
private import internal.ExpressionStatement
private import internal.FunctionDeclaration
private import internal.IfAltStatement
private import internal.IfStatement
private import internal.ImportStatement
private import internal.LexicalDeclaration
private import internal.ReturnStatement
private import internal.Statement
private import internal.StatementList
private import internal.SwitchStatement
private import internal.TryStatement

/**
 * A Stmt block
 */
final class Stmts extends AstNode instanceof StmtsImpl { }

/**
 *  Represents a sequence of statements.
 */
final class StmtSequence extends AstNode instanceof StmtSequenceImpl {
  Stmts getStmts() { result = StmtSequenceImpl.super.getStmts() }

  Stmts getStmt(int index) { result = StmtSequenceImpl.super.getStmt(index) }
}

/**
 * A Program statement sequence
 */
class Program extends StmtSequence instanceof ProgramImpl { }

/**
 * A StatementBlock statement sequence
 */
class StatementBlock extends StmtSequence instanceof StatementBlockImpl { }

/**
 * A BreakStatement statement
 */
class BreakStatement extends Stmts instanceof BreakStatementImpl { }

/**
 * A ContinueStatement statement
 */
class ContinueStatement extends Stmts instanceof ContinueStatementImpl { }

/**
 * A Declaration statement
 */
class Declaration extends Stmts instanceof DeclarationImpl { }

/**
 * A EmptyStatement statement
 */
class EmptyStatement extends Stmts instanceof EmptyStatementImpl { }

/**
 * A ExportStatement statement
 */
class ExportStatement extends Stmts instanceof ExportStatementImpl { }

/**
 * A ExpressionStatement statement
 */
class ExpressionStatement extends Stmts instanceof ExpressionStatementImpl { }

/**
 * A FunctionDeclaration statement
 */
class FunctionDeclaration extends Stmts instanceof FunctionDeclarationImpl { }

/**
 * A IfAltStatement statement
 */
class IfAltStatement extends Stmts instanceof IfAltStatementImpl { }

/**
 * A IfStatement statement
 */
class IfStatement extends Stmts instanceof IfStatementImpl { }

/**
 * A ImportStatement statement
 */
class ImportStatement extends Stmts instanceof ImportStatementImpl { }

/**
 * A LexicalDeclaration statement
 */
class LexicalDeclaration extends Stmts instanceof LexicalDeclarationImpl { }

/**
 * A ReturnStatement statement
 */
class ReturnStatement extends Stmts instanceof ReturnStatementImpl { }

/**
 * A Statement statement
 */
class Statement extends Stmts instanceof StatementImpl { }

/**
 * A StatementList statement
 */
class StatementList extends Stmts instanceof StatementListImpl { }

/**
 * A SwitchStatement statement
 */
class SwitchStatement extends Stmts instanceof SwitchStatementImpl { }

/**
 * A TryStatement statement
 */
class TryStatement extends Stmts instanceof TryStatementImpl { }

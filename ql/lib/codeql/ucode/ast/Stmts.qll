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
// Statements
private import internal.BreakStatement
private import internal.ContinueStatement
private import internal.Declaration
private import internal.EmptyStatement
private import internal.ExportStatement
private import internal.ExpressionStatement
private import internal.ForAltStatement
private import internal.ForInAltStatement
private import internal.ForInStatement
private import internal.ForStatement
private import internal.FunctionDeclaration
private import internal.IfAltStatement
private import internal.IfStatement
private import internal.ImportStatement
private import internal.LexicalDeclaration
private import internal.ReturnStatement
private import internal.Statement
private import internal.StatementBlock
private import internal.StatementList
private import internal.SwitchStatement
private import internal.TryStatement
private import internal.WhileAltStatement
private import internal.WhileStatement
// CFG
private import codeql.ucode.CFG
private import codeql.ucode.controlflow.internal.ControlFlowGraphImpl as CfgImpl

/**
 * A Stmt block
 */
final class Stmts extends AstNode instanceof StmtsImpl {
  /** Gets a control-flow node for this statement, if any. */
  CfgImpl::AstCfgNode getAControlFlowNode() { result.getAstNode() = this }
  
  /** Gets a control-flow entry node for this statement, if any */
  AstNode getAControlFlowEntryNode() { result = CfgImpl::getAControlFlowEntryNode(this) }
}

/**
 *  Represents a sequents of statements.
 */
final class StmtSequence extends AstNode instanceof StmtSequenceImpl {
  Stmts getStmts() {
    result = StmtSequenceImpl.super.getStmts()
  }

  Stmts getStmt(int index) {
    result = StmtSequenceImpl.super.getStmt(index)
  }
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
 * A ForAltStatement statement
 */
class ForAltStatement extends Stmts instanceof ForAltStatementImpl { }
/**
 * A ForInAltStatement statement
 */
class ForInAltStatement extends Stmts instanceof ForInAltStatementImpl { }
/**
 * A ForInStatement statement
 */
class ForInStatement extends Stmts instanceof ForInStatementImpl { }
/**
 * A ForStatement statement
 */
class ForStatement extends Stmts instanceof ForStatementImpl { }
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
 * A StatementBlock statement
 */
class StatementBlock extends Stmts instanceof StatementBlockImpl { }
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
/**
 * A WhileAltStatement statement
 */
class WhileAltStatement extends Stmts instanceof WhileAltStatementImpl { }
/**
 * A WhileStatement statement
 */
class WhileStatement extends Stmts instanceof WhileStatementImpl { }

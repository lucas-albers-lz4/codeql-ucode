// Test-only immediate CFG edges, including exact source and destination spans.
import codeql.ucode.controlflow.ControlFlowGraph

from CfgNode a, CfgNode b
where
  b = a.getASuccessor() and
  a.getFile().getBaseName() = ["break.uc", "break_control.uc", "controls.uc"]
select a.getFile().getBaseName() as sourceFile,
  a.getLocation().getStartLine() as sourceLine,
  a.getLocation().getStartColumn() as sourceColumn,
  a.getLocation().getEndLine() as sourceEndLine,
  a.getLocation().getEndColumn() as sourceEndColumn,
  b.getFile().getBaseName() as targetFile,
  b.getLocation().getStartLine() as targetLine,
  b.getLocation().getStartColumn() as targetColumn,
  b.getLocation().getEndLine() as targetEndLine,
  b.getLocation().getEndColumn() as targetEndColumn

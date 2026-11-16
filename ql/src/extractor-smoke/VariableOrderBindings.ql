import codeql.ucode.AST

from VariableReadAccess a
where a.getName() = "x" and a.getLocation().getFile().getBaseName() = "order.uc"
select a.getLocation().getStartLine() as readLine, a.getLocation().getStartColumn() as readColumn,
  a.getVariable().getLocation().getStartLine() as declarationLine,
  a.getVariable().getLocation().getStartColumn() as declarationColumn

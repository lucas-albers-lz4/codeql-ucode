import codeql.ucode.AST

from VariableReadAccess a
where
  a.getName() = "x" or a.getName() = "y" or a.getName() = "q" or a.getName() = "i"
select a.getLocation().getFile().getBaseName() as file,
  a.getLocation().getStartLine() as readLine,
  a.getLocation().getStartColumn() as readColumn,
  a.getVariable().getLocation().getStartLine() as declarationLine,
  a.getVariable().getLocation().getStartColumn() as declarationColumn

import codeql.ucode.DataFlow

from DataFlow::SsaDefinitionNode src, DataFlow::SsaReadNode snk
where
  src.getLocation().getFile().getBaseName() = "scope.uc" and
  src.getDefinition().getSourceVariable().getName() = snk.getDefinition().getSourceVariable().getName() and
  DataFlow::localFlowStep+(src, snk)
select src.getDefinition().getSourceVariable().getName() as name,
  src.getLocation().getStartLine() as writeLine,
  src.getLocation().getStartColumn() as writeColumn,
  snk.getLocation().getStartLine() as readLine,
  snk.getLocation().getStartColumn() as readColumn

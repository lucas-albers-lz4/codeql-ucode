/**
 * @name SSA value-flow regression
 * @description Reports transitive value-flow endpoints in the isolated regression fixture.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/test/value-flow-regression
 */

import codeql.ucode.DataFlow

from DataFlow::SsaDefinitionNode src, DataFlow::SsaReadNode snk
where
  DataFlow::localFlowStep+(src, snk) and
  src.getLocation().getFile().getBaseName() = "ssa_pos"
select src,
  src.getDefinition().getSourceVariable().getName() + ":" +
    src.getLocation().getStartLine().toString() + " -> " +
    snk.getDefinition().getSourceVariable().getName() + ":" +
    snk.getDefinition().getLocation().getStartLine().toString() + ":" +
    snk.getLocation().getStartLine().toString()

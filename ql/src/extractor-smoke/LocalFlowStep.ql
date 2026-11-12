/**
 * @name Public DataFlow localFlowStep SSA pairs
 * @description SSA-identity localFlowStep+ from a write definition to a read.
 *              Testing only. Not production taint and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/local-flow-step
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.DataFlow

from DataFlow::SsaDefinitionNode src, DataFlow::SsaReadNode snk
where
  DataFlow::localFlowStep+(src, snk) and
  (
    src.getLocation().getFile().getBaseName() = "ssa_pos" or
    src.getLocation().getFile().getBaseName() = "ssa_neg"
  )
select src,
  src.getDefinition().getSourceVariable().getName() + " -> " +
    snk.getDefinition().getSourceVariable().getName() + " in " +
    snk.getLocation().getFile().getBaseName()
